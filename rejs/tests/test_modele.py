import datetime
from decimal import Decimal

from django.forms import ValidationError
from django.test import TestCase
from django.urls import reverse

from django.contrib.auth import get_user_model

from rejs.models import AuditLog, Dane_Dodatkowe, Ogloszenie, Rejs, Wachta, Wplata, Zgloszenie


# Helper to get future dates for tests
def future_date(days_from_now: int) -> str:
	"""Return a date string N days from today."""
	return (datetime.date.today() + datetime.timedelta(days=days_from_now)).isoformat()


class RejsModelTest(TestCase):
	"""Testy modelu Rejs."""

	def setUp(self):
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
			cena=Decimal("1500.00"),
			zaliczka=Decimal("500.00"),
			opis="Opis testowego rejsu",
		)

	def test_str_representation(self):
		"""Test reprezentacji tekstowej rejsu."""
		self.assertEqual(str(self.rejs), "Rejs testowy")

	def test_reszta_do_zaplaty(self):
		"""Test obliczania reszty do zapłaty."""
		self.assertEqual(self.rejs.reszta_do_zaplaty, Decimal("1000.00"))

	def test_reszta_do_zaplaty_custom_values(self):
		"""Test reszty do zapłaty z niestandardowymi wartościami."""
		rejs = Rejs.objects.create(
			nazwa="Rejs drogi",
			od=future_date(60),
			do=future_date(74),
			start="Gdańsk",
			koniec="Kopenhaga",
			cena=Decimal("2500.00"),
			zaliczka=Decimal("800.00"),
		)
		self.assertEqual(rejs.reszta_do_zaplaty, Decimal("1700.00"))


class WachtaModelTest(TestCase):
	"""Testy modelu Wachta."""

	def setUp(self):
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
		)
		self.wachta = Wachta.objects.create(rejs=self.rejs, nazwa="Alfa")

	def test_str_representation(self):
		"""Test reprezentacji tekstowej wachty."""
		self.assertEqual(str(self.wachta), "Wachta Alfa - Rejs testowy")


class ZgloszenieModelTest(TestCase):
	"""Testy modelu Zgloszenie."""

	def setUp(self):
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
			cena=Decimal("1500.00"),
			zaliczka=Decimal("500.00"),
		)
		self.zgloszenie = Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)

	def test_str_representation(self):
		"""Test reprezentacji tekstowej zgłoszenia."""
		self.assertEqual(str(self.zgloszenie), "Jan Kowalski")

	def test_token_generated_on_create(self):
		"""Test czy token UUID jest generowany przy tworzeniu."""
		self.assertIsNotNone(self.zgloszenie.token)

	def test_token_is_unique(self):
		"""Test unikalności tokena."""
		zgloszenie2 = Zgloszenie.objects.create(
			imie="Anna",
			nazwisko="Nowak",
			email="anna@example.com",
			telefon="987654321",
			data_urodzenia=datetime.date(1991, 2, 2),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)
		self.assertNotEqual(self.zgloszenie.token, zgloszenie2.token)

	def test_suma_wplat_empty(self):
		"""Test sumy wpłat gdy brak wpłat."""
		self.assertEqual(self.zgloszenie.suma_wplat, Decimal("0"))

	def test_suma_wplat_with_payments(self):
		"""Test sumy wpłat z wpłatami."""
		Wplata.objects.create(zgloszenie=self.zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata")
		Wplata.objects.create(zgloszenie=self.zgloszenie, kwota=Decimal("300.00"), rodzaj="wplata")
		self.assertEqual(self.zgloszenie.suma_wplat, Decimal("800.00"))

	def test_suma_wplat_with_zwroty(self):
		"""Test sumy wpłat z wpłatami i zwrotami."""
		Wplata.objects.create(zgloszenie=self.zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata")
		Wplata.objects.create(zgloszenie=self.zgloszenie, kwota=Decimal("100.00"), rodzaj="zwrot")
		self.assertEqual(self.zgloszenie.suma_wplat, Decimal("400.00"))

	def test_do_zaplaty_calculation(self):
		"""Test obliczania kwoty do zapłaty."""
		self.assertEqual(self.zgloszenie.do_zaplaty, Decimal("1500.00"))

		Wplata.objects.create(zgloszenie=self.zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata")
		self.assertEqual(self.zgloszenie.do_zaplaty, Decimal("1000.00"))

	def test_rejs_cena(self):
		"""Test właściwości rejs_cena."""
		self.assertEqual(self.zgloszenie.rejs_cena, Decimal("1500.00"))

	def test_clean_wachta_validation_same_rejs(self):
		"""Test walidacji - wachta z tego samego rejsu."""
		wachta = Wachta.objects.create(rejs=self.rejs, nazwa="Alfa")
		self.zgloszenie.wachta = wachta
		self.zgloszenie.clean()

	def test_clean_wachta_validation_different_rejs(self):
		"""Test walidacji - wachta z innego rejsu."""
		inny_rejs = Rejs.objects.create(
			nazwa="Inny rejs",
			od=future_date(60),
			do=future_date(74),
			start="Gdańsk",
			koniec="Helsinki",
		)
		wachta = Wachta.objects.create(rejs=inny_rejs, nazwa="Beta")
		self.zgloszenie.wachta = wachta

		with self.assertRaises(ValidationError):
			self.zgloszenie.clean()

	def test_get_absolute_url(self):
		"""Test generowania URL do szczegółów zgłoszenia."""
		url = self.zgloszenie.get_absolute_url()
		expected = reverse("zgloszenie_details", kwargs={"token": self.zgloszenie.token})
		self.assertEqual(url, expected)

	def test_wzrok_default_is_string(self):
		"""Domyślna wartość wzroku powinna być stringiem 'WIDZI', nie krotką."""
		zgloszenie = Zgloszenie(
			imie="Test",
			nazwisko="User",
			email="test@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)
		self.assertEqual(zgloszenie.wzrok, "WIDZI")
		self.assertIsInstance(zgloszenie.wzrok, str)
		self.assertNotIn("(", zgloszenie.wzrok)


class WplataModelTest(TestCase):
	"""Testy modelu Wplata."""

	def setUp(self):
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
		)
		self.zgloszenie = Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)

	def test_str_representation(self):
		"""Test reprezentacji tekstowej wpłaty."""
		wplata = Wplata.objects.create(zgloszenie=self.zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata")
		self.assertEqual(str(wplata), "Wpłata: 500.00 zł")

	def test_rodzaj_default_is_string(self):
		"""Domyślna wartość rodzaju wpłaty powinna być stringiem 'wplata', nie krotką."""
		wplata = Wplata(kwota=Decimal("100.00"), zgloszenie=self.zgloszenie)
		self.assertEqual(wplata.rodzaj, "wplata")
		self.assertIsInstance(wplata.rodzaj, str)
		self.assertNotIn("(", wplata.rodzaj)


class OgloszenieModelTest(TestCase):
	"""Testy modelu Ogloszenie."""

	def setUp(self):
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
		)
		self.ogloszenie = Ogloszenie.objects.create(
			rejs=self.rejs,
			tytul="Ważne ogłoszenie",
			text="Treść ogłoszenia dla uczestników rejsu.",
		)

	def test_str_representation(self):
		"""Test reprezentacji tekstowej ogłoszenia."""
		self.assertEqual(str(self.ogloszenie), "Ważne ogłoszenie")

	def test_default_values(self):
		"""Test domyślnych wartości pól."""
		ogloszenie = Ogloszenie.objects.create(rejs=self.rejs)
		self.assertEqual(ogloszenie.tytul, "nowe ogłoszenie")
		self.assertEqual(ogloszenie.text, "krótka informacja o rejsie")

	def test_data_auto_now_add(self):
		"""Test automatycznego ustawiania daty."""
		self.assertIsNotNone(self.ogloszenie.data)

	def test_rejs_relation(self):
		"""Test relacji z rejsem."""
		self.assertEqual(self.ogloszenie.rejs, self.rejs)
		self.assertIn(self.ogloszenie, self.rejs.ogloszenia.all())


class Dane_DodatkoweModelTest(TestCase):
	"""Testy modelu Dane_Dodatkowe z szyfrowaniem."""

	def setUp(self):
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
		)
		self.zgloszenie = Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)
		self.dane = Dane_Dodatkowe.objects.create(
			zgloszenie=self.zgloszenie,
			poz1="90021401384",
			poz2="paszport",
			poz3="ABC123456",
			zgoda_dane_wrazliwe=True,
		)

	def test_str_representation(self):
		"""Test reprezentacji tekstowej danych dodatkowych."""
		expected = f"dane dodatkowe dla zgłoszenia: {self.zgloszenie.id}"
		self.assertEqual(str(self.dane), expected)

	def test_encrypted_fields_stored_and_retrieved(self):
		"""Test czy zaszyfrowane pola są poprawnie zapisywane i odczytywane."""
		dane = Dane_Dodatkowe.objects.get(pk=self.dane.pk)
		self.assertEqual(dane.poz1, "90021401384")
		self.assertEqual(dane.poz2, "paszport")
		self.assertEqual(dane.poz3, "ABC123456")

	def test_masked_pesel(self):
		"""Test maskowania numeru PESEL."""
		# PESEL 90021401384: first 2 chars + (11-3=8) asterisks + last char
		self.assertEqual(self.dane.masked_pesel, "90********4")

	def test_masked_pesel_short(self):
		"""Test maskowania krótkiego PESEL."""
		self.dane.poz1 = "12345"
		self.assertEqual(self.dane.masked_pesel, "12**5")

	def test_masked_dokument(self):
		"""Test maskowania numeru dokumentu."""
		self.assertEqual(self.dane.masked_dokument, "A*******6")

	def test_masked_dokument_short(self):
		"""Test maskowania krótkiego numeru dokumentu."""
		self.dane.poz3 = "AB1"
		self.assertEqual(self.dane.masked_dokument, "A*1")

	def test_one_to_one_relation(self):
		"""Test relacji OneToOne ze zgłoszeniem."""
		self.assertEqual(self.dane.zgloszenie, self.zgloszenie)
		self.assertEqual(self.zgloszenie.dane_dodatkowe, self.dane)

	def test_zgoda_dane_wrazliwe_default(self):
		"""Test domyślnej wartości zgody na dane wrażliwe."""
		zgloszenie2 = Zgloszenie.objects.create(
			imie="Anna",
			nazwisko="Nowak",
			email="anna@example.com",
			telefon="987654321",
			data_urodzenia=datetime.date(1991, 2, 2),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)
		dane2 = Dane_Dodatkowe.objects.create(
			zgloszenie=zgloszenie2,
			poz1="91020212345",
			poz2="dowod-osobisty",
			poz3="XYZ789",
		)
		self.assertFalse(dane2.zgoda_dane_wrazliwe)

	def test_typ_dokumentu_default_is_string(self):
		"""Domyślna wartość typu dokumentu powinna być stringiem 'paszport', nie krotką."""
		dane = Dane_Dodatkowe(
			zgloszenie=self.zgloszenie,
			poz1="90021401384",
			poz3="ABC123",
		)
		self.assertEqual(dane.poz2, "paszport")
		self.assertIsInstance(dane.poz2, str)
		self.assertNotIn("(", dane.poz2)


class AuditLogModelTest(TestCase):
	"""Testy modelu AuditLog."""

	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="testuser",
			email="test@example.com",
			password="testpass123",
		)

	def test_str_representation_with_user(self):
		"""Test reprezentacji tekstowej logu z użytkownikiem."""
		log = AuditLog.objects.create(
			uzytkownik=self.user,
			akcja="odczyt",
			model_name="Dane_Dodatkowe",
			object_id=1,
		)
		str_repr = str(log)
		self.assertIn("testuser", str_repr)
		self.assertIn("Odczyt danych", str_repr)
		self.assertIn("Dane_Dodatkowe", str_repr)

	def test_str_representation_without_user(self):
		"""Test reprezentacji tekstowej logu bez użytkownika (systemowy)."""
		log = AuditLog.objects.create(
			akcja="usuniecie",
			model_name="Dane_Dodatkowe",
		)
		str_repr = str(log)
		self.assertIn("System", str_repr)
		self.assertIn("Usunięcie danych", str_repr)

	def test_akcja_choices(self):
		"""Test wszystkich dostępnych akcji."""
		akcje = ["odczyt", "utworzenie", "modyfikacja", "usuniecie", "eksport"]
		for akcja in akcje:
			log = AuditLog.objects.create(akcja=akcja, model_name="Test")
			self.assertEqual(log.akcja, akcja)

	def test_timestamp_auto_set(self):
		"""Test automatycznego ustawiania timestamp."""
		log = AuditLog.objects.create(akcja="odczyt", model_name="Test")
		self.assertIsNotNone(log.timestamp)

	def test_optional_fields(self):
		"""Test opcjonalnych pól."""
		log = AuditLog.objects.create(
			uzytkownik=self.user,
			akcja="eksport",
			model_name="Dane_Dodatkowe",
			object_id=42,
			object_repr="Jan Kowalski",
			ip_address="192.168.1.1",
			user_agent="Mozilla/5.0",
			szczegoly="Eksport do Excel",
		)
		self.assertEqual(log.object_id, 42)
		self.assertEqual(log.object_repr, "Jan Kowalski")
		self.assertEqual(log.ip_address, "192.168.1.1")
		self.assertEqual(log.user_agent, "Mozilla/5.0")
		self.assertEqual(log.szczegoly, "Eksport do Excel")

	def test_ordering(self):
		"""Test domyślnego sortowania (najnowsze pierwsze)."""
		log1 = AuditLog.objects.create(akcja="odczyt", model_name="Test1")
		log2 = AuditLog.objects.create(akcja="odczyt", model_name="Test2")
		logs = list(AuditLog.objects.all())
		self.assertEqual(logs[0], log2)
		self.assertEqual(logs[1], log1)
