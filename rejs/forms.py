from django import forms
from django.core.validators import RegexValidator

from .models import Zgloszenie, Dane_Dodatkowe

telefon_validator = RegexValidator(
	regex=r"^\+?\d{9,15}$",
	message="Numer telefonu musi zawierać 9-15 cyfr, opcjonalnie z + na początku.",
)


class ZgloszenieForm(forms.ModelForm):
	class Meta:
		model = Zgloszenie
		fields = ["imie", "nazwisko", "email", "telefon", "data_urodzenia", "wzrok", "obecnosc", "rodo"]
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

from django import forms
from django.core.validators import RegexValidator

from .models import Zgloszenie, Dane_Dodatkowe

class Dane_DodatkoweForm(forms.ModelForm):
	class Meta:
		model = Dane_Dodatkowe
		fields = ["poz1", "poz2", "poz3"]
		labels = {
			"poz1": "pesel",
			"poz2": "typ dokumentu",
			"poz3": "numer dokumentu",
		}
		help_texts = {
			"poz1": "podaj swój pesel",
			"poz2": "wybierz dokument który według procedur oddasz przy zaokrętowaniu się.",
			"poz3": "podaj numer dokumentu który oddasz przy zaokrętowaniu."
}
		widgets = {
			"poz1": forms.TextInput(
				attrs={
					"aria-required": "true",
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
