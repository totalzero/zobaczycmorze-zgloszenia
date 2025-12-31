"""
Serwis rejestracji na rejs.

Odpowiada za logikę biznesową związaną z rejestracją uczestników.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.timezone import localdate

if TYPE_CHECKING:
	from rejs.models import Dane_Dodatkowe, Rejs, Zgloszenie


class SerwisRejestracji:
	"""
	Serwis obsługujący logikę rejestracji na rejs.

	Metody:
		czy_mozna_rejestrowac - sprawdza czy rejestracja jest możliwa
		czy_duplikat - sprawdza czy zgłoszenie już istnieje
		czy_wymaga_danych_dodatkowych - sprawdza czy potrzebne są dane dodatkowe
	"""

	def czy_mozna_rejestrowac(self, rejs: Rejs) -> tuple[bool, str]:
		"""
		Sprawdza czy można zarejestrować się na dany rejs.

		Args:
			rejs: Rejs do sprawdzenia

		Returns:
			Krotka (czy_mozna, komunikat_bledu)
		"""
		if not rejs.aktywna_rekrutacja:
			return False, "Rekrutacja na ten rejs jest zamknięta."

		if rejs.od < localdate():
			return False, "Rejs już się rozpoczął."

		return True, ""

	def czy_duplikat(self, rejs: Rejs, imie: str, nazwisko: str, email: str) -> bool:
		"""
		Sprawdza czy istnieje już zgłoszenie dla danej osoby na dany rejs.

		Args:
			rejs: Rejs do sprawdzenia
			imie: Imię uczestnika
			nazwisko: Nazwisko uczestnika
			email: Email uczestnika

		Returns:
			True jeśli zgłoszenie już istnieje
		"""
		from rejs.models import Zgloszenie

		return Zgloszenie.objects.filter(
			rejs=rejs,
			imie__iexact=imie,
			nazwisko__iexact=nazwisko,
			email__iexact=email,
		).exists()

	def czy_wymaga_danych_dodatkowych(self, zgloszenie: Zgloszenie) -> bool:
		"""
		Sprawdza czy zgłoszenie wymaga uzupełnienia danych dodatkowych.

		Args:
			zgloszenie: Zgłoszenie do sprawdzenia

		Returns:
			True jeśli wymagane są dane dodatkowe
		"""
		from rejs.models import Zgloszenie as ZgloszenieModel

		if zgloszenie.status != ZgloszenieModel.STATUS_ZAKWALIFIKOWANY:
			return False

		return not hasattr(zgloszenie, "dane_dodatkowe")


# Domyślna instancja serwisu
serwis_rejestracji = SerwisRejestracji()
