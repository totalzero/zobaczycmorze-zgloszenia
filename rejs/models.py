import datetime
import uuid
import base64
from decimal import Decimal
from django.db import models
from django.db.models import Case, Sum, When
from django.forms import ValidationError
from django.urls import reverse
from cryptography.fernet import Fernet
from django.conf import settings

fernet = Fernet(settings.DJANGO_FIELD_ENCRYPTION_KEY.encode())

class EncryptedTextField(models.TextField):
	def from_db_value(self, value, expression, connection):
		if value is None:
			return value
		return fernet.decrypt(value.encode()).decode()

	def get_prep_value(self, value):
		if value is None:
			return value
		return fernet.encrypt(value.encode()).decode()


class Rejs(models.Model):
	nazwa = models.CharField(max_length=200, null=False, blank=False)
	od = models.DateField(null=False, blank=False, verbose_name="data od")
	do = models.DateField(null=False, blank=False, verbose_name="data do")
	start = models.CharField(
		max_length=200, null=False, blank=False, verbose_name="port początkowy"
	)
	koniec = models.CharField(
		max_length=200, null=False, blank=False, verbose_name="port końcowy"
	)
	cena = models.DecimalField(default=1500, max_digits=10, decimal_places=2)
	zaliczka = models.DecimalField(default=500, max_digits=10, decimal_places=2)
	opis = models.TextField(default="tutaj opis rejsu", blank=False, null=False)

	def __str__(self) -> str:
		return self.nazwa

	@property
	def reszta_do_zaplaty(self):
		return self.cena - self.zaliczka

	class Meta:
		verbose_name = "Rejs"
		verbose_name_plural = "Rejsy"


class Wachta(models.Model):
	rejs = models.ForeignKey(Rejs, on_delete=models.CASCADE, related_name="wachty")
	nazwa = models.CharField(max_length=200)

	class Meta:
		verbose_name = "Wachta"
		verbose_name_plural = "Wachty"

	def __str__(self):
		return f"Wachta {self.nazwa} - {self.rejs}"


class Zgloszenie(models.Model):
	statusy = [
		("QUALIFIED", "Zakwalifikowany"),
		("NOT_QUALIFIED", "Niezakwalifikowany"),
		("ODRZUCONE", "Odrzucone"),
	]
	wzrok_statusy = [
		("WIDZI", "widzący"),
		("NIEWIDOMY", "niewidomy"),
		("SLABO-WIDZACY", "słabo widzący"),
	]
	role_pola = [("ZALOGANT", "załogant"), ("OFICER-WACHTY", "oficer wachty")]
	obecnosc_pola = [("tak", "tak"), ("nie", "nie")]

	imie = models.CharField(
		max_length=100, null=False, blank=False, verbose_name="Imię"
	)
	nazwisko = models.CharField(
		max_length=100, null=False, blank=False, verbose_name="Nazwisko"
	)
	email = models.EmailField(null=False, blank=False, verbose_name="Adres e-mail")
	telefon = models.CharField(
		max_length=15, blank=False, null=False, verbose_name="Numer telefonu"
	)
	data_urodzenia = models.DateField(blank=False, null=False, verbose_name="data urodzenia", default=datetime.date.today())
	obecnosc = models.CharField(
		max_length=3,
		choices=obecnosc_pola,
		verbose_name="uczestnictwo w zobaczyć morze")
	rodo = models.BooleanField(verbose_name="zgoda na przetwarzanie danych osobowych", help_text="zgadzam się na przetwarzanie danych osobowych zgodnie z polityką prywatności zobaczyć morze.")
	status = models.CharField(max_length=20, choices=statusy, default=statusy[1])
	wzrok = models.CharField(
		max_length=15,
		choices=wzrok_statusy,
		default=wzrok_statusy[0],
		verbose_name="Status wzroku",
	)
	rola = models.CharField(max_length=25, default="ZALOGANT", choices=role_pola)
	rejs = models.ForeignKey(Rejs, on_delete=models.CASCADE, related_name="zgloszenia")
	wachta = models.ForeignKey(
		Wachta,
		related_name="czlonkowie",
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
	)
	token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	data_zgloszenia = models.DateTimeField(auto_now_add=True, editable=False)

	@property
	def suma_wplat(self) -> Decimal:
		"""Oblicza sumę wpłat minus zwroty (zoptymalizowane - jedno zapytanie SQL)."""
		result = self.wplaty.aggregate(
			wplaty_sum=Sum(
				Case(
					When(rodzaj="wplata", then="kwota"),
					default=Decimal("0"),
				)
			),
			zwroty_sum=Sum(
				Case(
					When(rodzaj="zwrot", then="kwota"),
					default=Decimal("0"),
				)
			),
		)
		wplaty = result["wplaty_sum"] or Decimal("0")
		zwroty = result["zwroty_sum"] or Decimal("0")
		return wplaty - zwroty

	@property
	def rejs_cena(self):
		return self.rejs.cena

	@property
	def do_zaplaty(self):
		return self.rejs.cena - self.suma_wplat

	def __str__(self):
		return f"{self.imie} {self.nazwisko}"

	def clean(self):
		if self.wachta and self.wachta.rejs_id != self.rejs_id:
			raise ValidationError(
				"Wachta musi należeć do tego samego rejsu co zgłoszenie."
			)

	def get_absolute_url(self):
		return reverse("zgloszenie_details", kwargs={"token": self.token})

	class Meta:
		verbose_name = "Zgłoszenie"
		verbose_name_plural = "Zgłoszenia"


class Wplata(models.Model):
	rodzaje = [("wplata", "Wpłata"), ("zwrot", "Zwrot")]
	kwota = models.DecimalField(
		default=0, blank=False, null=False, max_digits=10, decimal_places=2
	)
	data = models.DateTimeField(auto_now_add=True)
	rodzaj = models.CharField(max_length=7, default=rodzaje[1], choices=rodzaje)
	zgloszenie = models.ForeignKey(
		Zgloszenie,
		related_name="wplaty",
		on_delete=models.CASCADE,
		blank=True,
		null=True,
	)

	class Meta:
		verbose_name = "Wpłata"
		verbose_name_plural = "Wpłaty"

	def __str__(self):
		return f"Wpłata: {self.kwota} zł"


class Ogloszenie(models.Model):
	rejs = models.ForeignKey(Rejs, on_delete=models.CASCADE, related_name="ogloszenia")
	data = models.DateTimeField(auto_now_add=True)
	tytul = models.CharField(
		default="nowe ogłoszenie",
		max_length=100,
		null=False,
		blank=False,
		verbose_name="Tytuł",
	)
	text = models.TextField(default="krótka informacja o rejsie", verbose_name="Tekst")

	class Meta:
		verbose_name = "Ogłoszenie"
		verbose_name_plural = "Ogłoszenia"

	def __str__(self):
		return self.tytul

class Dane_Dodatkowe(models.Model):
	typ_dokumentu = [
		("paszport", "paszport"),
		("dowod-osobisty", "dowód osobisty")
	]
	
	zgloszenie = models.OneToOneField(
		Zgloszenie,
		on_delete=models.CASCADE,
		related_name="dane_dodatkowe"
	)
	poz1 = EncryptedTextField(max_length=13,
						   null = False,
						   blank=False,
						   default="12345678900",
						   verbose_name="pesel")
	poz2 = EncryptedTextField(max_length=14,
								  choices=typ_dokumentu,
								  default=typ_dokumentu[0],
								  verbose_name="typ dokumentu")
	poz3 = EncryptedTextField(blank=False,
						   null=False,
						   default="ABC123",
						   verbose_name="numer dokumentu")
	class Meta:
		verbose_name = "dane dodatkowe"
		verbose_name_plural = "dane dodatkowe"

	def __str__(self) -> str:
		return f"dane dodatkowe dla zgłoszenia: {self.zgloszenie_id}"

	@property
	def masked_pesel(self):
		result = self.poz1[:2] + ("*" * (len(self.poz1) - 3)) + self.poz1[len(self.poz1) - 1]
		return result

	@property
	def masked_dokument(self):
		result = self.poz3[:1] + ("*" * len(self.poz3) - 2) + self.poz3[len(self.poz3) - 1]
		return result
