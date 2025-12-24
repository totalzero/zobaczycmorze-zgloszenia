from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from .models import Zgloszenie, Dane_Dodatkowe

telefon_validator = RegexValidator(
    regex=r"^\+?\d{9,15}$",
    message="Numer telefonu musi zawierać 9-15 cyfr, opcjonalnie z + na początku.",
)


def validate_pesel(pesel: str) -> str:
    """
    Waliduje numer PESEL zgodnie z polskim algorytmem sumy kontrolnej.

    Algorytm:
    1. PESEL musi mieć dokładnie 11 cyfr
    2. Suma kontrolna: każda cyfra mnożona przez wagę [1,3,7,9,1,3,7,9,1,3,1]
    3. Suma modulo 10 musi równać się 0
    """
    if not pesel:
        raise ValidationError("Numer PESEL jest wymagany.")

    cleaned = pesel.strip().replace(" ", "").replace("-", "")

    if len(cleaned) != 11:
        raise ValidationError("Numer PESEL musi składać się z dokładnie 11 cyfr.")

    if not cleaned.isdigit():
        raise ValidationError("Numer PESEL może zawierać tylko cyfry.")

    wagi = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3, 1]
    suma = sum(int(cyfra) * waga for cyfra, waga in zip(cleaned, wagi))

    if suma % 10 != 0:
        raise ValidationError("Nieprawidłowy numer PESEL - błędna suma kontrolna.")

    return cleaned


class ZgloszenieForm(forms.ModelForm):
    class Meta:
        model = Zgloszenie
        fields = [
            "imie",
            "nazwisko",
            "email",
            "telefon",
            "data_urodzenia",
            "wzrok",
            "obecnosc",
            "rodo",
        ]
        labels = {
            "imie": "Imię",
            "nazwisko": "Nazwisko",
            "email": "Adres e-mail",
            "telefon": "Numer telefonu",
            "data_urodzenia": "data urodzenia",
            "wzrok": "Status wzroku",
            "obecnosc": "udział w poprzednich rejsach",
            "rodo": "zgoda na przetwarzanie danych osobowych",
        }
        help_texts = {
            "telefon": "Format: 9-15 cyfr, np. 123456789 lub +48123456789",
            "data_urodzenia": "podaj date urodzenia w formacie dd.mm.rrrr - jako separatora uzyj kropek",
            "wzrok": "Wybierz opcję najbliższą Twojej sytuacji",
            "obecnosc": "Czy brałeś juz udział w rejsach zobaczyć morze?",
            "rodo": "czy zgadzasz się na przetwarzanie danych osobowych?",
        }
        widgets = {
            "imie": forms.TextInput(
                attrs={
                    "autocomplete": "given-name",
                    "aria-required": "true",
                }
            ),
            "nazwisko": forms.TextInput(
                attrs={
                    "autocomplete": "family-name",
                    "aria-required": "true",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "autocomplete": "email",
                    "aria-required": "true",
                }
            ),
            "telefon": forms.TextInput(
                attrs={
                    "autocomplete": "tel",
                    "inputmode": "tel",
                    "aria-required": "true",
                }
            ),
            "data_urodzenia": forms.DateInput(
                attrs={
                    "autocomplete": "bday",
                    "inputmode": "date",
                    "aria-required": "true",
                }
            ),
            "wzrok": forms.Select(
                attrs={
                    "aria-required": "true",
                }
            ),
            "obecnosc": forms.Select(
                attrs={
                    "aria-required": "true",
                }
            ),
            "rodo": forms.CheckboxInput(
                attrs={
                    "aria-required": "true",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            describedby = []
            if field.help_text:
                describedby.append(f"id_{field_name}-hint")
            if self.errors.get(field_name):
                describedby.append(f"id_{field_name}-error")
                field.widget.attrs["aria-invalid"] = "true"
            if describedby:
                field.widget.attrs["aria-describedby"] = " ".join(describedby)

    def clean_telefon(self):
        telefon = self.cleaned_data.get("telefon", "")
        cleaned = (
            telefon.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )
        telefon_validator(cleaned)
        return cleaned


class Dane_DodatkoweForm(forms.ModelForm):
    class Meta:
        model = Dane_Dodatkowe
        fields = ["poz1", "poz2", "poz3", "zgoda_dane_wrazliwe"]
        labels = {
            "poz1": "PESEL",
            "poz2": "Typ dokumentu",
            "poz3": "Numer dokumentu",
            "zgoda_dane_wrazliwe": "Zgoda na przetwarzanie danych",
        }
        help_texts = {
            "poz1": "Podaj swój numer PESEL (11 cyfr).",
            "poz2": "Wybierz dokument, który zgodnie z procedurami oddasz przy zaokrętowaniu.",
            "poz3": "Podaj numer dokumentu, który oddasz przy zaokrętowaniu.",
            "zgoda_dane_wrazliwe": "Wyrażam zgodę na przetwarzanie moich danych osobowych (PESEL, numer dokumentu) "
            "w celu realizacji procedur zaokrętowania zgodnie z wymogami kapitana. "
            "Dane zostaną usunięte w ciągu 30 dni po zakończeniu rejsu.",
        }
        widgets = {
            "poz1": forms.TextInput(
                attrs={
                    "aria-required": "true",
                    "inputmode": "numeric",
                    "maxlength": "11",
                    "pattern": "[0-9]{11}",
                }
            ),
            "poz2": forms.Select(
                attrs={
                    "aria-required": "true",
                }
            ),
            "poz3": forms.TextInput(
                attrs={
                    "aria-required": "true",
                }
            ),
            "zgoda_dane_wrazliwe": forms.CheckboxInput(
                attrs={
                    "aria-required": "true",
                }
            ),
        }

    def clean_poz1(self):
        pesel = self.cleaned_data.get("poz1", "")
        return validate_pesel(pesel)

    def clean_zgoda_dane_wrazliwe(self):
        zgoda = self.cleaned_data.get("zgoda_dane_wrazliwe")
        if not zgoda:
            raise forms.ValidationError(
                "Musisz wyrazić zgodę na przetwarzanie danych wrażliwych, aby kontynuować."
            )
        return zgoda

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            describedby = []
            if field.help_text:
                describedby.append(f"id_{field_name}-hint")
            if self.errors.get(field_name):
                describedby.append(f"id_{field_name}-error")
                field.widget.attrs["aria-invalid"] = "true"
            if describedby:
                field.widget.attrs["aria-describedby"] = " ".join(describedby)
