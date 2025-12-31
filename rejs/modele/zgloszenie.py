"""
Modele związane ze zgłoszeniami uczestników.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Case, Sum, When
from django.forms import ValidationError
from django.urls import reverse

from rejs.modele.pola import EncryptedTextField
from rejs.modele.rejs import Rejs, Wachta

if TYPE_CHECKING:
	from django.db.models.manager import RelatedManager

	from rejs.modele.finanse import Wplata


class Zgloszenie(models.Model):
	STATUS_ZAKWALIFIKOWANY = "Zakwalifikowany"
	STATUS_NIEZAKWALIFIKOWANY = "Niezakwalifikowany"
	STATUS_ODRZUCONE = "Odrzucone"
	statusy = [
		(STATUS_NIEZAKWALIFIKOWANY, "Niezakwalifikowany"),
		(STATUS_ZAKWALIFIKOWANY, "Zakwalifikowany"),
		(STATUS_ODRZUCONE, "Odrzucone"),
	]
	wzrok_statusy = [
		("WIDZI", "widzący"),
		("NIEWIDOMY", "niewidomy"),
		("SLABO-WIDZACY", "słabo widzący"),
	]
	role_pola = [("ZALOGANT", "załogant"), ("OFICER-WACHTY", "oficer wachty")]
	obecnosc_pola = [("tak", "tak"), ("nie", "nie")]

	imie = models.CharField(max_length=100, null=False, blank=False, verbose_name="Imię")
	nazwisko = models.CharField(max_length=100, null=False, blank=False, verbose_name="Nazwisko")
	email = models.EmailField(null=False, blank=False, verbose_name="Adres e-mail")
	telefon = models.CharField(max_length=15, blank=False, null=False, verbose_name="Numer telefonu")
	data_urodzenia = models.DateField(blank=False, null=False, verbose_name="Data urodzenia")
	adres = models.CharField(null=False, blank=False, default="", verbose_name="Adres")
	kod_pocztowy = models.CharField(null=False, blank=False, default="", verbose_name="Kod pocztowy")
	miejscowosc = models.CharField(null=False, blank=False, default="", verbose_name="Miejscowość")
	obecnosc = models.CharField(
		max_length=3,
		choices=obecnosc_pola,
		verbose_name="Uczestnictwo w Zobaczyć Morze",
	)
	rodo = models.BooleanField(
		verbose_name="Zgoda na przetwarzanie danych osobowych",
		help_text="Zgadzam się na przetwarzanie danych osobowych zgodnie z polityką prywatności Zobaczyć Morze.",
	)
	status = models.CharField(max_length=20, choices=statusy, default=STATUS_NIEZAKWALIFIKOWANY)
	wzrok = models.CharField(
		max_length=15,
		choices=wzrok_statusy,
		default=wzrok_statusy[0][0],
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
	token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
	data_zgloszenia = models.DateTimeField(auto_now_add=True, editable=False)

	if TYPE_CHECKING:
		wplaty: RelatedManager[Wplata]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# Śledź oryginalne wartości po załadowaniu z bazy danych
		# Używane przez sygnały do wykrywania zmian bez dodatkowego zapytania DB
		self._original_status = self.status if self.pk else None
		self._original_wachta_id = self.wachta_id if self.pk else None

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		# Po zapisie aktualizuj oryginalne wartości dla kolejnych zmian
		self._original_status = self.status
		self._original_wachta_id = self.wachta_id

	@classmethod
	def from_db(cls, db, field_names, values):
		"""Nadpisuje from_db aby śledzić oryginalne wartości przy ładowaniu z DB."""
		instance = super().from_db(db, field_names, values)
		instance._original_status = instance.status
		instance._original_wachta_id = instance.wachta_id
		return instance

	@property
	def suma_wplat(self) -> Decimal:
		"""Oblicza sumę wpłat minus zwroty (zoptymalizowane - jedno zapytanie SQL)."""
		from rejs.modele.finanse import Wplata

		result = self.wplaty.aggregate(
			wplaty_sum=Sum(
				Case(
					When(rodzaj=Wplata.RODZAJ_WPLATA, then="kwota"),
					default=Decimal("0"),
				)
			),
			zwroty_sum=Sum(
				Case(
					When(rodzaj=Wplata.RODZAJ_ZWROT, then="kwota"),
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
			raise ValidationError("Wachta musi należeć do tego samego rejsu co zgłoszenie.")

	def get_absolute_url(self):
		return reverse("zgloszenie_details", kwargs={"token": self.token})

	class Meta:
		app_label = "rejs"
		verbose_name = "Zgłoszenie"
		verbose_name_plural = "Zgłoszenia"
		constraints = [
			models.UniqueConstraint(
				fields=["rejs", "imie", "nazwisko", "email"],
				name="unique_zgloszenie_na_rejs_dla_osoby",
			)
		]


class Dane_Dodatkowe(models.Model):
	typ_dokumentu = [("paszport", "paszport"), ("dowod-osobisty", "dowód osobisty")]

	zgloszenie = models.OneToOneField(Zgloszenie, on_delete=models.CASCADE, related_name="dane_dodatkowe")
	poz1 = EncryptedTextField(
		max_length=13,
		null=False,
		blank=False,
		default="12345678900",
		verbose_name="PESEL",
	)
	poz2 = EncryptedTextField(
		max_length=14,
		choices=typ_dokumentu,
		default=typ_dokumentu[0][0],
		verbose_name="Typ dokumentu",
	)
	poz3 = EncryptedTextField(blank=False, null=False, default="ABC123", verbose_name="Numer dokumentu")
	zgoda_dane_wrazliwe = models.BooleanField(
		default=False,
		verbose_name="Zgoda na przetwarzanie danych wrażliwych",
		help_text="Wyrażam zgodę na przetwarzanie moich danych osobowych (PESEL, numer dokumentu) "
		"w celu realizacji procedur zaokrętowania zgodnie z wymogami kapitana. "
		"Dane zostaną usunięte w ciągu 30 dni po zakończeniu rejsu.",
	)

	class Meta:
		app_label = "rejs"
		verbose_name = "Dane dodatkowe"
		verbose_name_plural = "Dane dodatkowe"
		permissions = [
			("export_sensitive_data", "Może eksportować dane wrażliwe do raportów"),
		]

	def __str__(self) -> str:
		return f"dane dodatkowe dla zgłoszenia: {self.zgloszenie_id}"

	@staticmethod
	def _mask_value(value: str, prefix_len: int, suffix_len: int) -> str:
		"""Maskuje wartość, pozostawiając widoczny prefix i suffix."""
		if len(value) <= prefix_len + suffix_len:
			return "*" * len(value)
		masked_len = len(value) - prefix_len - suffix_len
		return value[:prefix_len] + ("*" * masked_len) + value[-suffix_len:]

	@property
	def masked_pesel(self):
		return self._mask_value(self.poz1, prefix_len=2, suffix_len=1)

	@property
	def masked_dokument(self):
		return self._mask_value(self.poz3, prefix_len=1, suffix_len=1)
