from django.shortcuts import get_object_or_404, redirect, render

from .forms import Dane_DodatkoweForm, ZgloszenieForm
from .models import Rejs, Zgloszenie


def index(request):
	rejsy = Rejs.objects.all().order_by("od")
	return render(request, "rejs/index.html", {"rejsy": rejsy})


def zgloszenie_utworz(request, rejs_id):
	rejs = get_object_or_404(Rejs, id=rejs_id)
	if request.method == "POST":
		form = ZgloszenieForm(request.POST)
		if form.is_valid():
			zgl = form.save(commit=False)
			zgl.rejs = rejs
			zgl.save()
			return redirect("zgloszenie_details", token=zgl.token)
	else:
		form = ZgloszenieForm()

	return render(request, "rejs/zgloszenie_form.html", {"form": form, "rejs": rejs})

def dane_dodatkowe_form(request, token):
	zgloszenie = get_object_or_404(Zgloszenie, token=token)
	rejs = zgloszenie.rejs
	if request.method == "POST":
		form = Dane_DodatkoweForm(request.POST)
		if form.is_valid():
			dane = form.save(commit=False)
			dane.zgloszenie = zgloszenie
			dane.save()
			return redirect(zgloszenie.get_absolute_url())
	else:
			form = Dane_DodatkoweForm()
		
	return render(request, 'rejs/dane_dodatkowe_form.html', {
		"form": form,
		"zgloszenie": zgloszenie,
		"rejs": rejs
	})

def zgloszenie_details(request, token):
	zgloszenie = get_object_or_404(Zgloszenie, token=token)
	if zgloszenie.status in ["QUALIFIED", "Zakwalifikowany"] and not hasattr(zgloszenie, "dane_dodatkowe"):
		return redirect('dane_dodatkowe_form', token=token)
	return render(request, "rejs/zgloszenie_details.html", {"zgloszenie": zgloszenie})
