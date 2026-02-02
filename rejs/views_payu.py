import json
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from rejs.payu import PayUClient
from .models import PlatnoscPayU, Wplata, Zgloszenie
from .payu_verify import verify_payu_signature


@csrf_exempt
def payu_webhook(request):
	# 1️⃣ weryfikacja podpisu
	if not verify_payu_signature(request):
		return HttpResponseForbidden("Invalid signature")

	data = json.loads(request.body)
	order = data.get("order")

	if not order:
		return HttpResponse("NO ORDER", status=400)

	order_id = order["orderId"]
	status = order["status"]

	try:
		platnosc = PlatnoscPayU.objects.select_related("zgloszenie").get(
			payu_order_id=order_id
		)
	except PlatnoscPayU.DoesNotExist:
		return HttpResponse("UNKNOWN ORDER", status=404)

	# 2️⃣ idempotencja
	if platnosc.status == PlatnoscPayU.STATUS_COMPLETED:
		return HttpResponse("OK")

	# 3️⃣ obsługa statusów
	if status == PlatnoscPayU.STATUS_COMPLETED:
		platnosc.status = PlatnoscPayU.STATUS_COMPLETED
		platnosc.save()

		Wplata.objects.get_or_create(
			zgloszenie=platnosc.zgloszenie,
			zrodlo_id=order_id,
			defaults={
				"kwota": platnosc.kwota,
				"rodzaj": Wplata.RODZAJ_PAYU,
				"opis": f"PayU – {platnosc.typ}",
			}
		)

	elif status in ("FAILED", "CANCELED"):
		platnosc.status = PlatnoscPayU.STATUS_FAILED
		platnosc.save()

	return HttpResponse("OK")


def zaplac(request, token, typ):
	zgl = get_object_or_404(Zgloszenie, token=token)

	if typ == "zaliczka":
		kwota = zgl.rejs.zaliczka

	elif typ == "reszta":
		if zgl.status != Zgloszenie.STATUS_ZAKWALIFIKOWANY:
			raise Http404()
		kwota = zgl.do_zaplaty

	else:
		raise Http404()

	platnosc = PlatnoscPayU.objects.create(
		zgloszenie=zgl,
		kwota=kwota,
		typ=typ,
	)

	client = PayUClient()
	result = client.create_order(
		kwota=kwota,
		opis=f"{zgl.rejs.nazwa} – {typ}",
		email=zgl.email,
		notify_url=request.build_absolute_uri("/payu/webhook/"),
		continue_url=request.build_absolute_uri(
		f"/payu/continue/{zgl.token}/{platnosc.id}/"
)

	)

	platnosc.payu_order_id = result["orderId"]
	platnosc.status = PlatnoscPayU.STATUS_PENDING
	platnosc.save()

	return redirect(result["redirectUri"])


@csrf_exempt
def payu_continue(request, token, platnosc_id):
	zgloszenie = get_object_or_404(Zgloszenie, token=token)

	platnosc = get_object_or_404(
		PlatnoscPayU.objects.select_related("zgloszenie"),
		id=platnosc_id,
		zgloszenie=zgloszenie
	)

	if not platnosc.payu_order_id:
		return render(request, "payu/error.html", {
			"message": "Brak powiązania z PayU."
		})

	client = PayUClient()

	try:
		data = client.get_order(platnosc.payu_order_id)
	except Exception:
		return render(request, "payu/error.html", {
			"message": "Nie udało się pobrać statusu płatności z PayU."
		})

	order = data["orders"][0]
	status = order["status"]

	# 🔁 synchronizacja statusu
	if platnosc.status != status:
		platnosc.status = status
		platnosc.save()

	# 💰 wpłata – IDEMPOTENTNIE
	if status == PlatnoscPayU.STATUS_COMPLETED:
		Wplata.objects.get_or_create(
			zgloszenie=zgloszenie,
			zrodlo_id=platnosc.payu_order_id,
			defaults={
				"kwota": platnosc.kwota,
				"rodzaj": Wplata.RODZAJ_PAYU,
				"opis": f"PayU – {platnosc.typ}",
			}
		)

	return render(request, "payu/summary.html", {
		"status": status,
		"kwota": platnosc.kwota,
		"order_id": platnosc.payu_order_id,
		"zgloszenie": zgloszenie,
	})
