import json
import hmac
import hashlib
from datetime import date

from django.test import TestCase, Client
from django.conf import settings

from rejs.models import Rejs, Zgloszenie, PlatnoscPayU, Wplata


class PayUWebhookTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.rejs = Rejs.objects.create(
            nazwa="Testowy rejs",
            od=date(2025, 6, 1),
            do=date(2025, 6, 10),
            start="Gdynia",
            koniec="Gdańsk",
            cena=1500,
            zaliczka=500,
        )

        self.zgloszenie = Zgloszenie.objects.create(
            imie="Jan",
            nazwisko="Kowalski",
            email="jan@test.pl",
            telefon="123456789",
            status=Zgloszenie.STATUS_ZAKWALIFIKOWANY,
            data_urodzenia=date(2000, 1, 1),
            wzrok="WIDZI",
            obecnosc="tak",
            adres="Chrzanowa 1a",
            miejscowosc="Warszawa",
            kod_pocztowy="00-001",
            rodo=True,
            rejs=self.rejs,
        )

        self.platnosc = PlatnoscPayU.objects.create(
            zgloszenie=self.zgloszenie,
            typ="zaliczka",
            kwota=500,
            payu_order_id="TEST_ORDER_1",
            status=PlatnoscPayU.STATUS_PENDING,
        )

    def sign(self, body: bytes) -> str:
        secret = settings.PAYU["WEBHOOK_SECRET"].encode()
        signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return f"sender=payu;signature=sha256={signature}"

    def test_completed_payment_creates_wplata(self):
        payload = {
            "order": {
                "orderId": "TEST_ORDER_1",
                "status": "COMPLETED",
            }
        }

        body = json.dumps(payload).encode()
        signature = self.sign(body)

        response = self.client.post(
            "/payu/webhook/",
            data=body,
            content_type="application/json",
            HTTP_OPENPAYU_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200)

        self.platnosc.refresh_from_db()
        self.assertEqual(
            self.platnosc.status,
            PlatnoscPayU.STATUS_COMPLETED
        )

        self.assertEqual(
            Wplata.objects.filter(
                zgloszenie=self.zgloszenie,
                rodzaj=Wplata.RODZAJ_PAYU,
                zrodlo_id="TEST_ORDER_1",
            ).count(),
            1,
        )

    def test_webhook_without_signature_is_rejected(self):
        payload = {
            "order": {
                "orderId": "TEST_ORDER_1",
                "status": "COMPLETED",
            }
        }

        response = self.client.post(
            "/payu/webhook/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Wplata.objects.count(), 0)

    def test_webhook_is_idempotent(self):
        payload = {
            "order": {
                "orderId": "TEST_ORDER_1",
                "status": "COMPLETED",
            }
        }

        body = json.dumps(payload).encode()
        signature = self.sign(body)

        self.client.post(
            "/payu/webhook/",
            data=body,
            content_type="application/json",
            HTTP_OPENPAYU_SIGNATURE=signature,
        )

        self.client.post(
            "/payu/webhook/",
            data=body,
            content_type="application/json",
            HTTP_OPENPAYU_SIGNATURE=signature,
        )

        self.assertEqual(
            Wplata.objects.filter(
                zgloszenie=self.zgloszenie,
                zrodlo_id="TEST_ORDER_1",
            ).count(),
            1,
        )
