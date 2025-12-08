import uuid
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms import ValidationError
from django.urls import reverse

class Rejs(models.Model):
	nazwa = models.CharField(max_length=200, null=False, blank=False)
	od = models.DateField(null=False, blank=False)
	do = models.DateField(null=False, blank=False)
	start = models.CharField(max_length=200, null=False, blank=False)
	koniec = models.CharField(max_length=200, null=False, blank=False)
	cena = models.DecimalField(default=1500, max_digits=10, decimal_places=2)
	zaliczka = models.DecimalField(default=500, max_digits=10, decimal_places=2)
	opis = models.TextField(default="tutaj opis rejsu", blank=False, null=False)
	def __str__(self) -> str:
		return self.nazwa
	class Meta:
		verbose_name = "Rejs"
		verbose_name_plural = "Rejsy"

class Wachta(models.Model):
	rejs = models.ForeignKey(Rejs, on_delete=models.CASCADE, related_name='wachty')
	nazwa=models.CharField(max_length=200)

	class Meta:
		verbose_name = "wachta"
		verbose_name_plural = "wachty"

	def __str__(self):
		return f"wachta {self.nazwa} - {self.rejs}"

class Zgloszenie(models.Model):
	statusy = [
		("QUALIFIED", "zakfalifikowany"),
		("NOT_QUALIFIED", "nie zakfalifikowany"),
		("odrzocone", "odrzocone")
	]
	wzrok_statusy = [
		("WIDZI", "widzący"),
		("SLEPY", "niewidomy"),
		("SLABO", "słabo widzący")
	]
	imie = models.CharField(max_length=100, null=False, blank=False)
	nazwisko = models.CharField(max_length=100, null=False, blank=False)
	email = models.EmailField(null=False, blank=False)
	telefon = models.CharField(max_length=15, blank=False, null=False)
	status = models.CharField(max_length=20, choices=statusy, default=statusy[1])
	wzrok = models.CharField(max_length=6, choices=wzrok_statusy, default=wzrok_statusy[0])
	rejs = models.ForeignKey(Rejs, on_delete=models.CASCADE, related_name='zgloszenia')
	wachta = models.ForeignKey(Wachta, related_name="czlonkowie", on_delete=models.SET_NULL, null=True, blank=True)
	token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	def __str__(self):
		return f"{self.imie} {self.nazwisko}"
	def clean(self):
		if self.wachta and self.wachta.rejs_id != self.rejs_id:
			raise ValidationError(
				"wachta musi nalezeć do tego samego rejsu co zgłoszenie"
			)

	def get_absolute_url(self):
		return reverse('zgloszenie_details', kwargs={"token": self.token})

	class Meta:
		verbose_name = "Zgłoszenie"
		verbose_name_plural = "Zgłoszenia"

class Finanse(models.Model):
	kwota_do_zaplaty = models.DecimalField(default=0, null=False, blank=False, verbose_name="kwota do zapłaty", max_digits=10, decimal_places=2)
	zgloszenie = models.OneToOneField(Zgloszenie, on_delete=models.CASCADE, related_name='finanse')
	class Meta:
		verbose_name = "finanse"
		verbose_name_plural = "finanse"

	@property
	def suma_wplat(self):
		wynik = self.wplaty.aggregate(total=Sum("kwota"))
		return wynik['total'] or 0
	
	@property
	def do_zaplaty(self):
		return self.kwota_do_zaplaty - self.suma_wplat
	
	def __str__(self):
		return f"Finanse #{self.id} {self.zgloszenie}"

class Wplata(models.Model):
	kwota = models.DecimalField(default=0, blank=False, null=False, max_digits=10, decimal_places=2)
	finanse = models.ForeignKey(Finanse, on_delete=models.CASCADE, related_name="wplaty")
	data = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "wpłata"
		verbose_name_plural = "wpłaty"

	def __str__(self):
		return f"Wpłata: {self.kwota} zł"

class Info(models.Model):
	rejs = models.ForeignKey(Rejs, on_delete=models.CASCADE)
	data = models.DateTimeField(auto_now_add=True)
	text = models.TextField(default="krótka informacja o rejsie")
	def __str__(self):
		return self.text
