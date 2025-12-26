import datetime
import uuid
from decimal import Decimal
from django.db import models
from django.db.models import Case, Sum, When
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
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
    data_urodzenia = models.DateField(
        blank=False,
        null=False,
        verbose_name="data urodzenia",
        default=datetime.date.today(),
    )
    adres = models.CharField(
        null=False, blank=False, default="unknown", verbose_name="adres"
    )
    kod_pocztowy = models.CharField(
        null=False, blank=False, default="00-000", verbose_name="kod pocztowy"
    )
    miejscowosc = models.CharField(
        null=False, blank=False, default="unknown", verbose_name="miejscowość"
    )
    obecnosc = models.CharField(
        max_length=3,
        choices=obecnosc_pola,
        verbose_name="uczestnictwo w zobaczyć morze",
    )
    rodo = models.BooleanField(
        verbose_name="zgoda na przetwarzanie danych osobowych",
        help_text="zgadzam się na przetwarzanie danych osobowych zgodnie z polityką prywatności zobaczyć morze.",
    )
    status = models.CharField(
        max_length=20, choices=statusy, default=STATUS_NIEZAKWALIFIKOWANY
    )
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
    typ_dokumentu = [("paszport", "paszport"), ("dowod-osobisty", "dowód osobisty")]

    zgloszenie = models.OneToOneField(
        Zgloszenie, on_delete=models.CASCADE, related_name="dane_dodatkowe"
    )
    poz1 = EncryptedTextField(
        max_length=13,
        null=False,
        blank=False,
        default="12345678900",
        verbose_name="pesel",
    )
    poz2 = EncryptedTextField(
        max_length=14,
        choices=typ_dokumentu,
        default=typ_dokumentu[0],
        verbose_name="typ dokumentu",
    )
    poz3 = EncryptedTextField(
        blank=False, null=False, default="ABC123", verbose_name="numer dokumentu"
    )
    zgoda_dane_wrazliwe = models.BooleanField(
        default=False,
        verbose_name="zgoda na przetwarzanie danych wrażliwych",
        help_text="Wyrażam zgodę na przetwarzanie moich danych osobowych (PESEL, numer dokumentu) "
        "w celu realizacji procedur zaokrętowania zgodnie z wymogami kapitana. "
        "Dane zostaną usunięte w ciągu 30 dni po zakończeniu rejsu.",
    )

    class Meta:
        verbose_name = "dane dodatkowe"
        verbose_name_plural = "dane dodatkowe"
        permissions = [
            ("export_sensitive_data", "Może eksportować dane wrażliwe do raportów"),
        ]

    def __str__(self) -> str:
        return f"dane dodatkowe dla zgłoszenia: {self.zgloszenie_id}"

    @property
    def masked_pesel(self):
        result = (
            self.poz1[:2] + ("*" * (len(self.poz1) - 3)) + self.poz1[len(self.poz1) - 1]
        )
        return result

    @property
    def masked_dokument(self):
        result = (
            self.poz3[:1] + ("*" * (len(self.poz3) - 2)) + self.poz3[len(self.poz3) - 1]
        )
        return result


class AuditLog(models.Model):
    """
    Model przechowujący logi dostępu do danych wrażliwych.

    Zgodnie z Art. 30 RODO - rejestr czynności przetwarzania.
    """

    AKCJA_CHOICES = [
        ("odczyt", "Odczyt danych"),
        ("utworzenie", "Utworzenie danych"),
        ("modyfikacja", "Modyfikacja danych"),
        ("usuniecie", "Usunięcie danych"),
        ("eksport", "Eksport danych"),
    ]

    timestamp = models.DateTimeField(
        default=timezone.now, verbose_name="Data i czas", db_index=True
    )
    uzytkownik = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Użytkownik",
        related_name="audit_logs",
    )
    akcja = models.CharField(max_length=20, choices=AKCJA_CHOICES, verbose_name="Akcja")
    model_name = models.CharField(max_length=100, verbose_name="Model")
    object_id = models.PositiveIntegerField(
        verbose_name="ID obiektu", null=True, blank=True
    )
    object_repr = models.CharField(
        max_length=200, verbose_name="Reprezentacja obiektu", blank=True
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="Adres IP"
    )
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    szczegoly = models.TextField(blank=True, verbose_name="Szczegóły operacji")

    class Meta:
        verbose_name = "Log audytu"
        verbose_name_plural = "Logi audytu"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["uzytkownik", "timestamp"]),
        ]

    def __str__(self):
        user_str = self.uzytkownik.username if self.uzytkownik else "System"
        return f"{self.timestamp:%Y-%m-%d %H:%M} | {user_str} | {self.get_akcja_display()} | {self.model_name}"
