import datetime
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase

from rejs.admin import Dane_DodatkoweAdmin, RejsyAdmin, ZgloszenieAdmin, generate_report
from rejs.models import AuditLog, Dane_Dodatkowe, Rejs, Zgloszenie


# Helper to get future dates for tests
def future_date(days_from_now: int) -> str:
	"""Return a date string N days from today."""
	return (datetime.date.today() + datetime.timedelta(days=days_from_now)).isoformat()


class AdminTest(TestCase):
	"""Testy panelu administracyjnego."""

	def setUp(self):
		self.client = Client()
		self.admin_user = User.objects.create_superuser(
			username="admin", email="admin@example.com", password="adminpass123"
		)
		self.client.login(username="admin", password="adminpass123")
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
		)

	def test_rejs_admin_accessible(self):
		"""Test dostępności admina rejsów."""
		response = self.client.get("/admin/rejs/rejs/")
		self.assertEqual(response.status_code, 200)

	def test_rejs_admin_add(self):
		"""Test dodawania rejsu przez admin."""
		response = self.client.get("/admin/rejs/rejs/add/")
		self.assertEqual(response.status_code, 200)

	def test_zgloszenie_admin_accessible(self):
		"""Test dostępności admina zgłoszeń."""
		response = self.client.get("/admin/rejs/zgloszenie/")
		self.assertEqual(response.status_code, 200)

	def test_zgloszenie_admin_change(self):
		"""Test edycji zgłoszenia przez admin."""
		zgloszenie = Zgloszenie.objects.create(
			imie="Jan",
			nazwisko="Kowalski",
			email="jan@example.com",
			telefon="123456789",
			data_urodzenia=datetime.date(1990, 1, 1),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)
		response = self.client.get(f"/admin/rejs/zgloszenie/{zgloszenie.id}/change/")
		self.assertEqual(response.status_code, 200)

	def test_rejs_admin_has_inlines(self):
		"""Test czy admin rejsu ma inline'y."""
		site = AdminSite()
		admin = RejsyAdmin(Rejs, site)
		self.assertEqual(len(admin.inlines), 3)

	def test_zgloszenie_admin_has_readonly_fields(self):
		"""Test czy admin zgłoszenia ma pola tylko do odczytu."""
		site = AdminSite()
		admin = ZgloszenieAdmin(Zgloszenie, site)
		self.assertIn("rejs_cena", admin.readonly_fields)
		self.assertIn("do_zaplaty", admin.readonly_fields)
		self.assertIn("suma_wplat", admin.readonly_fields)


class GenerateReportActionTest(TestCase):
	"""Testy akcji generowania raportu Excel."""

	def setUp(self):
		self.factory = RequestFactory()
		self.admin_user = User.objects.create_superuser(
			username="admin",
			email="admin@example.com",
			password="adminpass123",
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
		self.site = AdminSite()
		self.modeladmin = RejsyAdmin(Rejs, self.site)

	def test_generate_report_single_rejs(self):
		"""Test generowania raportu dla jednego rejsu."""
		request = self.factory.get("/admin/rejs/rejs/")
		request.user = self.admin_user

		queryset = Rejs.objects.filter(pk=self.rejs.pk)
		response = generate_report(self.modeladmin, request, queryset)

		self.assertIsNotNone(response)
		self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

	def test_generate_report_creates_audit_log(self):
		"""Test czy generowanie raportu tworzy wpis w logu audytu."""
		request = self.factory.get("/admin/rejs/rejs/")
		request.user = self.admin_user
		request.META["REMOTE_ADDR"] = "127.0.0.1"

		initial_count = AuditLog.objects.count()
		queryset = Rejs.objects.filter(pk=self.rejs.pk)
		generate_report(self.modeladmin, request, queryset)

		self.assertEqual(AuditLog.objects.count(), initial_count + 1)
		log = AuditLog.objects.latest("timestamp")
		self.assertEqual(log.akcja, "eksport")
		self.assertEqual(log.model_name, "Rejs")
		self.assertEqual(log.object_id, self.rejs.pk)

	def test_generate_report_multiple_rejs_error(self):
		"""Test błędu przy próbie generowania raportu dla wielu rejsów."""
		Rejs.objects.create(
			nazwa="Drugi rejs",
			od=future_date(60),
			do=future_date(74),
			start="Gdańsk",
			koniec="Helsinki",
		)

		request = self.factory.get("/admin/rejs/rejs/")
		request.user = self.admin_user
		request._messages = MockMessages()

		queryset = Rejs.objects.all()
		result = generate_report(self.modeladmin, request, queryset)

		self.assertIsNone(result)

	def test_generate_report_no_rejs_error(self):
		"""Test błędu przy próbie generowania raportu bez wybranego rejsu."""
		request = self.factory.get("/admin/rejs/rejs/")
		request.user = self.admin_user
		request._messages = MockMessages()

		queryset = Rejs.objects.none()
		result = generate_report(self.modeladmin, request, queryset)

		self.assertIsNone(result)


class MockMessages:
	"""Mock dla systemu wiadomości Django."""

	def __init__(self):
		self.messages = []

	def add(self, level, message, extra_tags):
		self.messages.append((level, message))


class Dane_DodatkoweAdminAuditTest(TestCase):
	"""Testy logowania audytu przy dostępie do danych wrażliwych."""

	def setUp(self):
		self.client = Client()
		self.admin_user = User.objects.create_superuser(
			username="admin",
			email="admin@example.com",
			password="adminpass123",
		)
		self.client.login(username="admin", password="adminpass123")
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
			data_urodzenia=datetime.date(1990, 1, 14),
			rejs=self.rejs,
			rodo=True,
			obecnosc="tak",
		)
		self.dane = Dane_Dodatkowe.objects.create(
			zgloszenie=self.zgloszenie,
			poz1="90011412345",
			poz2="paszport",
			poz3="ABC123",
		)

	def test_change_view_creates_audit_log(self):
		"""Test czy podgląd danych wrażliwych tworzy wpis w logu audytu."""
		initial_count = AuditLog.objects.count()

		response = self.client.get(f"/admin/rejs/dane_dodatkowe/{self.dane.pk}/change/")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(AuditLog.objects.count(), initial_count + 1)

		log = AuditLog.objects.latest("timestamp")
		self.assertEqual(log.akcja, "odczyt")
		self.assertEqual(log.model_name, "Dane_Dodatkowe")
		self.assertEqual(log.object_id, self.dane.pk)
		self.assertEqual(log.uzytkownik, self.admin_user)

	def test_audit_log_contains_details(self):
		"""Test czy log audytu zawiera szczegóły operacji."""
		self.client.get(f"/admin/rejs/dane_dodatkowe/{self.dane.pk}/change/")

		log = AuditLog.objects.latest("timestamp")
		self.assertIn("Podgląd danych wrażliwych", log.szczegoly)

	def test_list_view_does_not_create_audit_log(self):
		"""Test czy lista danych wrażliwych nie tworzy wpisu w logu."""
		initial_count = AuditLog.objects.count()

		response = self.client.get("/admin/rejs/dane_dodatkowe/")

		self.assertEqual(response.status_code, 200)
		# Lista nie powinna tworzyć logu (tylko change_view)
		self.assertEqual(AuditLog.objects.count(), initial_count)


class AuditLogAdminPermissionsTest(TestCase):
	"""Testy uprawnień admina logów audytu."""

	def setUp(self):
		self.site = AdminSite()
		self.factory = RequestFactory()
		self.admin_user = User.objects.create_superuser(
			username="admin",
			email="admin@example.com",
			password="adminpass123",
		)
		self.regular_user = User.objects.create_user(
			username="regular",
			email="regular@example.com",
			password="regularpass123",
			is_staff=True,
		)

	def test_has_add_permission_returns_false(self):
		"""Test czy dodawanie logów jest zablokowane."""
		from rejs.admin import AuditLogAdmin

		admin = AuditLogAdmin(AuditLog, self.site)
		request = self.factory.get("/admin/rejs/auditlog/add/")
		request.user = self.admin_user

		self.assertFalse(admin.has_add_permission(request))

	def test_has_change_permission_returns_false(self):
		"""Test czy edycja logów jest zablokowana."""
		from rejs.admin import AuditLogAdmin

		admin = AuditLogAdmin(AuditLog, self.site)
		request = self.factory.get("/admin/rejs/auditlog/1/change/")
		request.user = self.admin_user

		self.assertFalse(admin.has_change_permission(request))

	def test_has_delete_permission_superuser(self):
		"""Test czy superuser może usuwać logi."""
		from rejs.admin import AuditLogAdmin

		admin = AuditLogAdmin(AuditLog, self.site)
		request = self.factory.get("/admin/rejs/auditlog/")
		request.user = self.admin_user

		self.assertTrue(admin.has_delete_permission(request))

	def test_has_delete_permission_regular_user(self):
		"""Test czy zwykły użytkownik nie może usuwać logów."""
		from rejs.admin import AuditLogAdmin

		admin = AuditLogAdmin(AuditLog, self.site)
		request = self.factory.get("/admin/rejs/auditlog/")
		request.user = self.regular_user

		self.assertFalse(admin.has_delete_permission(request))


class WachtaFormTest(TestCase):
	"""Testy formularza WachtaForm w adminie."""

	def setUp(self):
		self.rejs = Rejs.objects.create(
			nazwa="Rejs testowy",
			od=future_date(30),
			do=future_date(44),
			start="Gdynia",
			koniec="Sztokholm",
		)

	def test_invalid_rejs_id_handled_gracefully(self):
		"""Test że nieprawidłowy rejs_id nie powoduje błędu ValueError."""
		from rejs.admin import WachtaForm

		# Symulacja formularza z nieprawidłowym rejs_id (nienumeryczny string)
		form = WachtaForm(data={"rejs": "invalid_id", "nazwa": "Test"})
		# Nie powinno rzucić wyjątku, queryset powinien być pusty
		self.assertEqual(form.fields["czlonkowie"].queryset.count(), 0)
