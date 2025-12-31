import datetime

from django.test import TestCase

from rejs.models import Rejs, Zgloszenie
from rejs.serwisy.rejestracja import SerwisRejestracji


# Helper to get future dates for tests
def future_date(days_from_now: int) -> datetime.date:
	"""Return a date N days from today."""
	return datetime.date.today() + datetime.timedelta(days=days_from_now)


def past_date(days_ago: int) -> datetime.date:
	"""Return a date N days ago."""
	return datetime.date.today() - datetime.timedelta(days=days_ago)


class SerwisRejestracjiTest(TestCase):
	"""Testy SerwisRejestracji."""

	def setUp(self):
		self.serwis = SerwisRejestracji()
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
			aktywna_rekrutacja=True,
		)

	def test_czy_mozna_rejestrowac_aktywny_rejs(self):
		"""Test czy można rejestrować na aktywny rejs."""
		mozna, komunikat = self.serwis.czy_mozna_rejestrowac(self.rejs)
		self.assertTrue(mozna)
		self.assertEqual(komunikat, "")

	def test_czy_mozna_rejestrowac_nieaktywna_rekrutacja(self):
		"""Test czy nie można rejestrować gdy rekrutacja nieaktywna."""
		self.rejs.aktywna_rekrutacja = False
		self.rejs.save()

		mozna, komunikat = self.serwis.czy_mozna_rejestrowac(self.rejs)
		self.assertFalse(mozna)
		self.assertIn("zamknięta", komunikat)

	def test_czy_mozna_rejestrowac_rejs_w_przeszlosci(self):
		"""Test czy nie można rejestrować na rejs który już się rozpoczął."""
		rejs_przeszly = Rejs.objects.create(
			nazwa="Rejs przeszły",
			od=past_date(10),
			do=past_date(1),
			start="Gdynia",
			koniec="Sztokholm",
			aktywna_rekrutacja=True,
		)

		mozna, komunikat = self.serwis.czy_mozna_rejestrowac(rejs_przeszly)
		self.assertFalse(mozna)
		self.assertIn("rozpoczął", komunikat)

	def test_czy_duplikat_brak_duplikatu(self):
		"""Test czy_duplikat gdy nie ma duplikatu."""
		wynik = self.serwis.czy_duplikat(self.rejs, "Jan", "Kowalski", "jan@example.com")
		self.assertFalse(wynik)

	def test_czy_duplikat_istnieje_duplikat(self):
		"""Test czy_duplikat gdy istnieje duplikat."""
		Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)

		wynik = self.serwis.czy_duplikat(self.rejs, "Jan", "Kowalski", "jan@example.com")
		self.assertTrue(wynik)

	def test_czy_duplikat_case_insensitive(self):
		"""Test czy_duplikat ignoruje wielkość liter."""
		Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)

		wynik = self.serwis.czy_duplikat(self.rejs, "JAN", "KOWALSKI", "JAN@EXAMPLE.COM")
		self.assertTrue(wynik)

	def test_czy_duplikat_inny_rejs(self):
		"""Test czy_duplikat nie wykrywa duplikatu na innym rejsie."""
		inny_rejs = Rejs.objects.create(
			nazwa="Inny rejs",
			od=future_date(60),
			do=future_date(74),
			start="Gdańsk",
			koniec="Helsinki",
		)
		Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=inny_rejs,
			rodo=True,
			obecnosc="tak",
		)

		wynik = self.serwis.czy_duplikat(self.rejs, "Jan", "Kowalski", "jan@example.com")
		self.assertFalse(wynik)

	def test_czy_wymaga_danych_dodatkowych_niezakwalifikowany(self):
		"""Test czy_wymaga_danych_dodatkowych dla niezakwalifikowanego."""
		zgloszenie = Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
			status=Zgloszenie.STATUS_NIEZAKWALIFIKOWANY,
		)

		wynik = self.serwis.czy_wymaga_danych_dodatkowych(zgloszenie)
		self.assertFalse(wynik)

	def test_czy_wymaga_danych_dodatkowych_zakwalifikowany_bez_danych(self):
		"""Test czy_wymaga_danych_dodatkowych dla zakwalifikowanego bez danych."""
		zgloszenie = Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
			status=Zgloszenie.STATUS_ZAKWALIFIKOWANY,
		)

		wynik = self.serwis.czy_wymaga_danych_dodatkowych(zgloszenie)
		self.assertTrue(wynik)

	def test_czy_wymaga_danych_dodatkowych_uses_model_constant(self):
		"""Test że metoda używa stałej STATUS_ZAKWALIFIKOWANY, nie magicznego stringa 'QUALIFIED'."""
		# Ten test weryfikuje że używamy polskiej stałej, nie angielskiego stringa
		zgloszenie = Zgloszenie.objects.create(
			imie="Test",
			nazwisko="User",
			email="test@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
			status="Zakwalifikowany",  # Bezpośredni string do weryfikacji
		)
		wynik = self.serwis.czy_wymaga_danych_dodatkowych(zgloszenie)
		self.assertTrue(wynik)
