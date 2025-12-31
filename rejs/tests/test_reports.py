import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from rejs.models import Dane_Dodatkowe, Rejs, Wachta, Wplata, Zgloszenie
from rejs.reports.builder import RaportRejsuBuilder


# Helper to get future dates for tests
def future_date(days_from_now: int) -> str:
	"""Return a date string N days from today."""
	return (datetime.date.today() + datetime.timedelta(days=days_from_now)).isoformat()


class RaportRejsuBuilderTest(TestCase):
	"""Testy klasy RaportRejsuBuilder."""

	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="testuser",
			email="test@example.com",
			password="testpass123",
		)
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
			data_urodzenia=datetime.date(1990, 1, 14),
			adres="ul. Testowa 1",
			kod_pocztowy="00-001",
			miejscowosc="Warszawa",
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
			status=Zgloszenie.STATUS_ZAKWALIFIKOWANY,
			wzrok="WIDZI",
			rola="ZALOGANT",
		)
		self.builder = RaportRejsuBuilder(self.rejs, self.user)

	def test_can_export_sensitive_without_permission(self):
		"""Test braku uprawnień do eksportu danych wrażliwych."""
		self.assertFalse(self.builder.can_export_sensitive())

	def test_can_export_sensitive_with_permission(self):
		"""Test z uprawnieniami do eksportu danych wrażliwych."""
		content_type = ContentType.objects.get_for_model(Dane_Dodatkowe)
		permission = Permission.objects.get(
			codename="export_sensitive_data",
			content_type=content_type,
		)
		self.user.user_permissions.add(permission)
		# Odświeżamy użytkownika aby załadować nowe uprawnienia
		self.user = get_user_model().objects.get(pk=self.user.pk)
		builder = RaportRejsuBuilder(self.rejs, self.user)

		self.assertTrue(builder.can_export_sensitive())

	def test_build_zaloga_returns_list(self):
		"""Test czy build_zaloga zwraca listę."""
		result = self.builder.build_zaloga()
		self.assertIsInstance(result, list)

	def test_build_zaloga_contains_zgloszenie_data(self):
		"""Test czy build_zaloga zawiera dane zgłoszenia."""
		result = self.builder.build_zaloga()

		self.assertEqual(len(result), 1)
		row = result[0]
		self.assertEqual(row["imie"], "Jan")
		self.assertEqual(row["nazwisko"], "Kowalski")
		self.assertEqual(row["email"], "jan@example.com")
		self.assertEqual(row["telefon"], "123456789")
		self.assertEqual(row["adres"], "ul. Testowa 1")
		self.assertEqual(row["kod pocztowy"], "00-001")
		self.assertEqual(row["miejscowość"], "Warszawa")
		self.assertEqual(row["status"], Zgloszenie.STATUS_ZAKWALIFIKOWANY)
		self.assertEqual(row["wzrok"], "WIDZI")
		self.assertEqual(row["rola"], "ZALOGANT")

	def test_build_zaloga_includes_financial_data(self):
		"""Test czy build_zaloga zawiera dane finansowe."""
		Wplata.objects.create(
			zgloszenie=self.zgloszenie,
			kwota=Decimal("500.00"),
			rodzaj="wplata",
		)

		result = self.builder.build_zaloga()
		row = result[0]

		self.assertEqual(row["suma_wplat"], Decimal("500.00"))
		self.assertEqual(row["do_zaplaty"], Decimal("1000.00"))

	def test_build_zaloga_includes_wachta(self):
		"""Test czy build_zaloga zawiera nazwę wachty."""
		wachta = Wachta.objects.create(rejs=self.rejs, nazwa="Alfa")
		self.zgloszenie.wachta = wachta
		self.zgloszenie.save()

		result = self.builder.build_zaloga()
		self.assertEqual(result[0]["wachta"], "Alfa")

	def test_build_zaloga_empty_wachta(self):
		"""Test build_zaloga gdy brak wachty."""
		result = self.builder.build_zaloga()
		self.assertEqual(result[0]["wachta"], "")

	def test_build_zaloga_multiple_zgloszenia(self):
		"""Test build_zaloga z wieloma zgłoszeniami."""
		Zgloszenie.objects.create(
			imie="Anna",
			nazwisko="Nowak",
			email="anna@example.com",
			telefon="987654321",
			data_urodzenia=datetime.date(1991, 2, 2),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)

		result = self.builder.build_zaloga()
		self.assertEqual(len(result), 2)

	def test_build_zaloga_only_current_rejs(self):
		"""Test czy build_zaloga zwraca tylko zgłoszenia z danego rejsu."""
		inny_rejs = Rejs.objects.create(
			nazwa="Inny rejs",
			od=future_date(60),
			do=future_date(74),
			start="Gdańsk",
			koniec="Helsinki",
		)
		Zgloszenie.objects.create(
			imie="Piotr",
			nazwisko="Wiśniewski",
			email="piotr@example.com",
			telefon="111222333",
			data_urodzenia=datetime.date(1985, 5, 5),
			rejs=inny_rejs,
			rodo=True,
			obecnosc="tak",
		)

		result = self.builder.build_zaloga()
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["imie"], "Jan")

	def test_build_wachty_returns_list(self):
		"""Test czy build_wachty zwraca listę."""
		result = self.builder.build_wachty()
		self.assertIsInstance(result, list)

	def test_build_wachty_empty(self):
		"""Test build_wachty gdy brak wacht."""
		result = self.builder.build_wachty()
		self.assertEqual(len(result), 0)

	def test_build_wachty_with_members(self):
		"""Test build_wachty z członkami."""
		wachta = Wachta.objects.create(rejs=self.rejs, nazwa="Alfa")
		self.zgloszenie.wachta = wachta
		self.zgloszenie.save()

		result = self.builder.build_wachty()

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["nazwa"], "Alfa")
		self.assertEqual(len(result[0]["czlonkowie"]), 1)
		self.assertEqual(result[0]["czlonkowie"][0]["imie"], "Jan")
		self.assertEqual(result[0]["czlonkowie"][0]["nazwisko"], "Kowalski")
		self.assertEqual(result[0]["czlonkowie"][0]["rola"], "ZALOGANT")

	def test_build_wachty_multiple(self):
		"""Test build_wachty z wieloma wachtami."""
		Wachta.objects.create(rejs=self.rejs, nazwa="Alfa")
		Wachta.objects.create(rejs=self.rejs, nazwa="Beta")

		result = self.builder.build_wachty()
		self.assertEqual(len(result), 2)

	def test_build_wplaty_returns_list(self):
		"""Test czy build_wplaty zwraca listę."""
		result = self.builder.build_wplaty()
		self.assertIsInstance(result, list)

	def test_build_wplaty_empty(self):
		"""Test build_wplaty gdy brak wpłat."""
		result = self.builder.build_wplaty()
		self.assertEqual(len(result), 0)

	def test_build_wplaty_with_payments(self):
		"""Test build_wplaty z wpłatami."""
		Wplata.objects.create(
			zgloszenie=self.zgloszenie,
			kwota=Decimal("500.00"),
			rodzaj="wplata",
		)

		result = self.builder.build_wplaty()

		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["imie"], "Jan")
		self.assertEqual(result[0]["nazwisko"], "Kowalski")
		self.assertEqual(result[0]["rodzaj"], "wplata")
		self.assertEqual(result[0]["kwota"], Decimal("500.00"))
		self.assertIsNotNone(result[0]["data"])

	def test_build_wplaty_includes_zwroty(self):
		"""Test build_wplaty zawiera zwroty."""
		Wplata.objects.create(
			zgloszenie=self.zgloszenie,
			kwota=Decimal("100.00"),
			rodzaj="zwrot",
		)

		result = self.builder.build_wplaty()
		self.assertEqual(result[0]["rodzaj"], "zwrot")

	def test_build_dane_wrazliwe_without_permission(self):
		"""Test build_dane_wrazliwe bez uprawnień."""
		Dane_Dodatkowe.objects.create(
			zgloszenie=self.zgloszenie,
			poz1="90011412345",
			poz2="paszport",
			poz3="ABC123",
		)

		result = self.builder.build_dane_wrazliwe()
		self.assertIsNone(result)

	def test_build_dane_wrazliwe_with_permission(self):
		"""Test build_dane_wrazliwe z uprawnieniami."""
		content_type = ContentType.objects.get_for_model(Dane_Dodatkowe)
		permission = Permission.objects.get(
			codename="export_sensitive_data",
			content_type=content_type,
		)
		self.user.user_permissions.add(permission)
		self.user = get_user_model().objects.get(pk=self.user.pk)
		builder = RaportRejsuBuilder(self.rejs, self.user)

		Dane_Dodatkowe.objects.create(
			zgloszenie=self.zgloszenie,
			poz1="90011412345",
			poz2="paszport",
			poz3="ABC123",
		)

		result = builder.build_dane_wrazliwe()

		self.assertIsNotNone(result)
		self.assertEqual(len(result), 1)
		self.assertEqual(result[0]["imie"], "Jan")
		self.assertEqual(result[0]["nazwisko"], "Kowalski")
		self.assertEqual(result[0]["pesel"], "90011412345")
		self.assertEqual(result[0]["typ_dokumentu"], "paszport")
		self.assertEqual(result[0]["dokument"], "ABC123")

	def test_build_dane_wrazliwe_empty_with_permission(self):
		"""Test build_dane_wrazliwe gdy brak danych wrażliwych."""
		content_type = ContentType.objects.get_for_model(Dane_Dodatkowe)
		permission = Permission.objects.get(
			codename="export_sensitive_data",
			content_type=content_type,
		)
		self.user.user_permissions.add(permission)
		self.user = get_user_model().objects.get(pk=self.user.pk)
		builder = RaportRejsuBuilder(self.rejs, self.user)

		result = builder.build_dane_wrazliwe()

		self.assertIsNotNone(result)
		self.assertEqual(len(result), 0)

	def test_build_zaloga_query_count(self):
		"""Test że build_zaloga nie powoduje N+1 zapytań."""
		from django.db import connection
		from django.test.utils import CaptureQueriesContext

		# Tworzymy 5 zgłoszeń z wpłatami
		for i in range(5):
			z = Zgloszenie.objects.create(
				imie=f"Test{i}",
				nazwisko=f"User{i}",
				email=f"test{i}@example.com",
				telefon=f"12345678{i}",
				data_urodzenia=datetime.date(1990, 1, 1),
				rejs=self.rejs,
				rodo=True,
				obecnosc="tak",
			)
			Wplata.objects.create(zgloszenie=z, kwota=Decimal("100.00"), rodzaj="wplata")
			Wplata.objects.create(zgloszenie=z, kwota=Decimal("50.00"), rodzaj="zwrot")

		# Powinno używać stałej liczby zapytań niezależnie od liczby wierszy
		# Z bugiem N+1: byłoby 1 + 5*2 = 11+ zapytań
		# Po naprawie: powinno być ~2-3 zapytania
		with CaptureQueriesContext(connection) as context:
			self.builder.build_zaloga()

		self.assertLess(len(context), 6, f"Za dużo zapytań: {len(context)}")
