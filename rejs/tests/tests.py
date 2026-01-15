from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from .admin import RejsyAdmin, ZgloszenieAdmin
from .forms import ZgloszenieForm
from .models import Ogloszenie, Rejs, Wachta, Wplata, Zgloszenie


class RejsModelTest(TestCase):
    """Testy modelu Rejs."""

    def setUp(self):
        self.rejs = Rejs.objects.create(
            nazwa="Rejs testowy",
            od="2025-07-01",
            do="2025-07-14",
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
            od="2025-08-01",
            do="2025-08-14",
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
            od="2025-07-01",
            do="2025-07-14",
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
            od="2025-07-01",
            do="2025-07-14",
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
            rejs=self.rejs,
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
            rejs=self.rejs,
        )
        self.assertNotEqual(self.zgloszenie.token, zgloszenie2.token)

    def test_suma_wplat_empty(self):
        """Test sumy wpłat gdy brak wpłat."""
        self.assertEqual(self.zgloszenie.suma_wplat, Decimal("0"))

    def test_suma_wplat_with_payments(self):
        """Test sumy wpłat z wpłatami."""
        Wplata.objects.create(
            zgloszenie=self.zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata"
        )
        Wplata.objects.create(
            zgloszenie=self.zgloszenie, kwota=Decimal("300.00"), rodzaj="wplata"
        )
        self.assertEqual(self.zgloszenie.suma_wplat, Decimal("800.00"))

    def test_suma_wplat_with_zwroty(self):
        """Test sumy wpłat z wpłatami i zwrotami."""
        Wplata.objects.create(
            zgloszenie=self.zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata"
        )
        Wplata.objects.create(
            zgloszenie=self.zgloszenie, kwota=Decimal("100.00"), rodzaj="zwrot"
        )
        self.assertEqual(self.zgloszenie.suma_wplat, Decimal("400.00"))

    def test_do_zaplaty_calculation(self):
        """Test obliczania kwoty do zapłaty."""
        self.assertEqual(self.zgloszenie.do_zaplaty, Decimal("1500.00"))

        Wplata.objects.create(
            zgloszenie=self.zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata"
        )
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
            od="2025-08-01",
            do="2025-08-14",
            start="Gdańsk",
            koniec="Helsinki",
        )
        wachta = Wachta.objects.create(rejs=inny_rejs, nazwa="Beta")
        self.zgloszenie.wachta = wachta

        from django.forms import ValidationError

        with self.assertRaises(ValidationError):
            self.zgloszenie.clean()

    def test_get_absolute_url(self):
        """Test generowania URL do szczegółów zgłoszenia."""
        url = self.zgloszenie.get_absolute_url()
        expected = reverse(
            "zgloszenie_details", kwargs={"token": self.zgloszenie.token}
        )
        self.assertEqual(url, expected)


class WplataModelTest(TestCase):
    """Testy modelu Wplata."""

    def setUp(self):
        self.rejs = Rejs.objects.create(
            nazwa="Rejs testowy",
            od="2025-07-01",
            do="2025-07-14",
            start="Gdynia",
            koniec="Sztokholm",
        )
        self.zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
        )

    def test_str_representation(self):
        """Test reprezentacji tekstowej wpłaty."""
        wplata = Wplata.objects.create(
            zgloszenie=self.zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata"
        )
        self.assertEqual(str(wplata), "Wpłata: 500.00 zł")


class IndexViewTest(TestCase):
    """Testy widoku listy rejsów."""

    def setUp(self):
        self.client = Client()

    def test_index_returns_200(self):
        """Test czy strona główna zwraca status 200."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

    def test_index_uses_correct_template(self):
        """Test czy używany jest prawidłowy szablon."""
        response = self.client.get(reverse("index"))
        self.assertTemplateUsed(response, "rejs/index.html")

    def test_index_displays_rejsy(self):
        """Test czy rejsy są wyświetlane."""
        Rejs.objects.create(
            nazwa="Rejs wakacyjny",
            od="2025-07-01",
            do="2025-07-14",
            start="Gdynia",
            koniec="Sztokholm",
        )
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Rejs wakacyjny")

    def test_index_empty_rejsy(self):
        """Test strony gdy brak rejsów."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["rejsy"]), 0)

    def test_index_rejsy_ordered_by_date(self):
        """Test czy rejsy są posortowane po dacie."""
        rejs2 = Rejs.objects.create(
            nazwa="Rejs późniejszy",
            od="2025-08-01",
            do="2025-08-14",
            start="Gdańsk",
            koniec="Helsinki",
        )
        rejs1 = Rejs.objects.create(
            nazwa="Rejs wcześniejszy",
            od="2025-07-01",
            do="2025-07-14",
            start="Gdynia",
            koniec="Sztokholm",
        )
        response = self.client.get(reverse("index"))
        rejsy = list(response.context["rejsy"])
        self.assertEqual(rejsy[0], rejs1)
        self.assertEqual(rejsy[1], rejs2)


class ZgloszenieCreateViewTest(TestCase):
    """Testy widoku tworzenia zgłoszenia."""

    def setUp(self):
        self.client = Client()
        self.rejs = Rejs.objects.create(
            nazwa="Rejs testowy",
            od="2025-07-01",
            do="2025-07-14",
            start="Gdynia",
            koniec="Sztokholm",
        )

    def test_get_form(self):
        """Test wyświetlania formularza."""
        response = self.client.get(
            reverse("zgloszenie_utworz", kwargs={"rejs_id": self.rejs.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rejs/zgloszenie_form.html")
        self.assertIsInstance(response.context["form"], ZgloszenieForm)

    def test_get_form_nonexistent_rejs(self):
        """Test formularza dla nieistniejącego rejsu."""
        response = self.client.get(
            reverse("zgloszenie_utworz", kwargs={"rejs_id": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_post_valid_form(self):
        """Test wysłania poprawnego formularza."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "123456789",
            "wzrok": "NIEWIDOMY",
        }
        response = self.client.post(
            reverse("zgloszenie_utworz", kwargs={"rejs_id": self.rejs.id}), data
        )
        self.assertEqual(Zgloszenie.objects.count(), 1)
        zgloszenie = Zgloszenie.objects.first()
        self.assertRedirects(
            response,
            reverse("zgloszenie_details", kwargs={"token": zgloszenie.token}),
        )

    def test_post_invalid_form_missing_fields(self):
        """Test wysłania formularza z brakującymi polami."""
        data = {
            "imie": "Jan",
        }
        response = self.client.post(
            reverse("zgloszenie_utworz", kwargs={"rejs_id": self.rejs.id}), data
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Zgloszenie.objects.count(), 0)
        self.assertFormError(
            response.context["form"], "nazwisko", "To pole jest wymagane."
        )

    def test_post_invalid_telefon(self):
        """Test wysłania formularza z nieprawidłowym telefonem."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "abc",
            "wzrok": "NIEWIDOMY",
        }
        response = self.client.post(
            reverse("zgloszenie_utworz", kwargs={"rejs_id": self.rejs.id}), data
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Zgloszenie.objects.count(), 0)


class ZgloszenieDetailsViewTest(TestCase):
    """Testy widoku szczegółów zgłoszenia."""

    def setUp(self):
        self.client = Client()
        self.rejs = Rejs.objects.create(
            nazwa="Rejs testowy",
            od="2025-07-01",
            do="2025-07-14",
            start="Gdynia",
            koniec="Sztokholm",
        )
        self.zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
        )

    def test_get_details_by_token(self):
        """Test wyświetlania szczegółów po tokenie."""
        response = self.client.get(
            reverse("zgloszenie_details", kwargs={"token": self.zgloszenie.token})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rejs/zgloszenie_details.html")
        self.assertEqual(response.context["zgloszenie"], self.zgloszenie)

    def test_invalid_token_returns_404(self):
        """Test 404 dla nieprawidłowego tokena."""
        import uuid

        fake_token = uuid.uuid4()
        response = self.client.get(
            reverse("zgloszenie_details", kwargs={"token": fake_token})
        )
        self.assertEqual(response.status_code, 404)

    def test_details_contains_personal_data(self):
        """Test czy szczegóły zawierają dane osobowe."""
        response = self.client.get(
            reverse("zgloszenie_details", kwargs={"token": self.zgloszenie.token})
        )
        self.assertContains(response, "Jan")
        self.assertContains(response, "Kowalski")


class ZgloszenieFormTest(TestCase):
    """Testy formularza zgłoszenia."""

    def test_valid_form(self):
        """Test poprawnego formularza."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "123456789",
            "wzrok": "NIEWIDOMY",
        }
        form = ZgloszenieForm(data=data)
        self.assertTrue(form.is_valid())

    def test_telefon_validation_9_digits(self):
        """Test walidacji telefonu - 9 cyfr."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "123456789",
            "wzrok": "NIEWIDOMY",
        }
        form = ZgloszenieForm(data=data)
        self.assertTrue(form.is_valid())

    def test_telefon_validation_with_plus(self):
        """Test walidacji telefonu z +."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "+48123456789",
            "wzrok": "NIEWIDOMY",
        }
        form = ZgloszenieForm(data=data)
        self.assertTrue(form.is_valid())

    def test_telefon_validation_15_digits(self):
        """Test walidacji telefonu - 15 cyfr."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "123456789012345",
            "wzrok": "NIEWIDOMY",
        }
        form = ZgloszenieForm(data=data)
        self.assertTrue(form.is_valid())

    def test_telefon_validation_invalid_letters(self):
        """Test walidacji telefonu - litery."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "abc123def",
            "wzrok": "NIEWIDOMY",
        }
        form = ZgloszenieForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("telefon", form.errors)

    def test_telefon_validation_too_short(self):
        """Test walidacji telefonu - za krótki."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "12345678",
            "wzrok": "NIEWIDOMY",
        }
        form = ZgloszenieForm(data=data)
        self.assertFalse(form.is_valid())

    def test_telefon_cleans_spaces_and_dashes(self):
        """Test czy telefon jest czyszczony ze spacji i myślników."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "jan@example.com",
            "telefon": "123-456-789",
            "wzrok": "NIEWIDOMY",
        }
        form = ZgloszenieForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["telefon"], "123456789")

    def test_required_fields(self):
        """Test wymaganych pól."""
        form = ZgloszenieForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("imie", form.errors)
        self.assertIn("nazwisko", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("telefon", form.errors)

    def test_invalid_email(self):
        """Test nieprawidłowego emaila."""
        data = {
            "imie": "Jan",
            "nazwisko": "Kowalski",
            "email": "nieprawidlowy-email",
            "telefon": "123456789",
            "wzrok": "NIEWIDOMY",
        }
        form = ZgloszenieForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


class SignalsTest(TestCase):
    """Testy sygnałów wysyłających emaile."""

    def setUp(self):
        self.rejs = Rejs.objects.create(
            nazwa="Rejs testowy",
            od="2025-07-01",
            do="2025-07-14",
            start="Gdynia",
            koniec="Sztokholm",
            cena=Decimal("1500.00"),
            zaliczka=Decimal("500.00"),
        )

    def test_email_sent_on_zgloszenie_create(self):
        """Test wysyłania emaila przy tworzeniu zgłoszenia."""
        Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Potwierdzenie zgłoszenia", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["jan@example.com"])

    def test_email_sent_on_status_change_qualified(self):
        """Test wysyłania emaila przy zmianie statusu na zakwalifikowany."""
        zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
            status="NOT_QUALIFIED",
        )
        mail.outbox.clear()

        zgloszenie.status = "QUALIFIED"
        zgloszenie.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("zakwalifikowanie", mail.outbox[0].subject)

    def test_email_sent_on_status_change_odrzucone(self):
        """Test wysyłania emaila przy zmianie statusu na odrzucone."""
        zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
            status="NOT_QUALIFIED",
        )
        mail.outbox.clear()

        zgloszenie.status = "ODRZUCONE"
        zgloszenie.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Odrzucone", mail.outbox[0].subject)

    def test_no_email_on_same_status(self):
        """Test braku emaila gdy status się nie zmienia."""
        zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
            status="NOT_QUALIFIED",
        )
        mail.outbox.clear()

        zgloszenie.imie = "Janusz"
        zgloszenie.save()

        self.assertEqual(len(mail.outbox), 0)

    def test_email_sent_on_wachta_assignment(self):
        """Test wysyłania emaila przy przypisaniu do wachty."""
        zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
        )
        wachta = Wachta.objects.create(rejs=self.rejs, nazwa="Alfa")
        mail.outbox.clear()

        zgloszenie.wachta = wachta
        zgloszenie.save()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("wachty", mail.outbox[0].subject)

    def test_email_sent_on_wplata_create(self):
        """Test wysyłania emaila przy tworzeniu wpłaty."""
        zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
        )
        mail.outbox.clear()

        Wplata.objects.create(
            zgloszenie=zgloszenie, kwota=Decimal("500.00"), rodzaj="wplata"
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("wpłatę", mail.outbox[0].subject)

    def test_email_sent_on_zwrot_create(self):
        """Test wysyłania emaila przy tworzeniu zwrotu."""
        zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
        )
        mail.outbox.clear()

        Wplata.objects.create(
            zgloszenie=zgloszenie, kwota=Decimal("100.00"), rodzaj="zwrot"
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Zwrot", mail.outbox[0].subject)

    def test_email_sent_on_ogloszenie_create(self):
        """Test wysyłania emaila przy tworzeniu ogłoszenia."""
        zgloszenie1 = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@example.com",
            telefon="123456789",
            rejs=self.rejs,
        )
        zgloszenie2 = Zgloszenie.objects.create(
            imie="Anna",
            nazwisko="Nowak",
            email="anna@example.com",
            telefon="987654321",
            rejs=self.rejs,
        )
        mail.outbox.clear()

        Ogloszenie.objects.create(
            rejs=self.rejs, tytul="Ważne ogłoszenie", text="Treść ogłoszenia"
        )

        self.assertEqual(len(mail.outbox), 2)
        recipients = [m.to[0] for m in mail.outbox]
        self.assertIn("jan@example.com", recipients)
        self.assertIn("anna@example.com", recipients)


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
            od="2025-07-01",
            do="2025-07-14",
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
            rejs=self.rejs,
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
