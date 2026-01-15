import json
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from .models import PlatnoscPayU, Wplata
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
	if status == "COMPLETED":
		platnosc.status = PlatnoscPayU.STATUS_COMPLETED
		platnosc.save()

		
		Wplata.objects.create(
			zgloszenie=platnosc.zgloszenie,
			kwota=platnosc.kwota,
			rodzaj=Wplata.RODZAJ_PAYU,
			opis=f"PayU – {platnosc.typ}",
			zrodlo_id=order_id,
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
		continue_url=request.build_absolute_uri(zgl.get_absolute_url()),
	)

	platnosc.payu_order_id = result["orderId"]
	platnosc.status = PlatnoscPayU.STATUS_PENDING
	platnosc.save()

	return redirect(result["redirectUri"])
