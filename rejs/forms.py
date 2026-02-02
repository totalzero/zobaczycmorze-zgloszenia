from django import forms
from django.core.validators import RegexValidator

from .models import Zgloszenie, Dane_Dodatkowe

telefon_validator = RegexValidator(
	regex=r"^\+?\d{9,15}$",
	message="Numer telefonu musi zawierać 9-15 cyfr, opcjonalnie z + na początku.",
)

kod_pocztowy_validator = RegexValidator(
	regex=r"^\d{2}-\d{3}$",
	message="Kod pocztowy musi mieć format XX-XXX (np. 00-001).",
)


class ZgloszenieForm(forms.ModelForm):
	class Meta:
		model = Zgloszenie
		fields = ["imie", "nazwisko", "plec", "email", "telefon", "data_urodzenia", "adres", "kod_pocztowy", "miejscowosc", "wzrok", "obecnosc", "rozmiar_koszulki", "uwagi", "rodo"]
		labels = {
			"imie": "Imię",
			"nazwisko": "Nazwisko",
			"plec": "Płeć",
			"email": "Adres e-mail",
			"telefon": "Numer telefonu",
			"data_urodzenia": "Data urodzenia",
			"adres": "Adres",
			"kod_pocztowy": "Kod pocztowy",
			"miejscowosc": "Miejscowość",
			"wzrok": "Status wzroku",
			"obecnosc": "Udział w poprzednich rejsach",
			"rozmiar_koszulki": "Rozmiar Koszulki",
			"uwagi": "Uwagi",
			"rodo": "Zgoda na przetwarzanie danych osobowych",
		}
		help_texts = {
			"telefon": "Format: 9-15 cyfr, np. 123456789 lub +48123456789",
			"data_urodzenia": "Podaj date urodzenia w formacie dd.mm.rrrr (np. 05.10.1990)",
			"kod_pocztowy": "Format: 00-000",
"wzrok": "Wybierz opcję najbliższą Twojej sytuacji",
			"obecnosc": "Czy brałeś juz udział w rejsach zobaczyć morze?",
			"rozmiar_koszulki": "wybierz swój właściwy rozmiar",
			"uwagi": "przekaż nam ważne informację o sobie.",
"rodo": "Zgadzam się na przetwarzanie danych osobowych.",
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
			"plec": forms.Select(
				attrs={
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
				format="%d.%m.%Y",
				attrs={
					"autocomplete": "bday",
					"inputmode": "date",
					"placeholder": "dd.mm.rrrr",
					"aria-required": "true",
				}
			),
			"adres": forms.TextInput(
				attrs={
					"aria-required": "true",
				}
			),
			"kod_pocztowy": forms.TextInput(
				attrs={
					"inputmode": "numeric",
					"aria-required": "true",
				}
			),
			"miejscowosc": forms.TextInput(
				attrs={
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
			"rozmiar_koszulki": forms.Select(
				attrs={
					"aria-required": "true",
				}
			),
			"uwagi": forms.Textarea(
				attrs= {
					"aria-required": "false",
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


	def clean(self):
		cleaned = super().clean()
		imie = cleaned.get("imie")
		nazwisko = cleaned.get("nazwisko")
		email = cleaned.get("email")

		if not (imie and nazwisko and email):
			return cleaned

		rejs = self.initial.get("rejs") or self.instance.rejs

		if rejs:
			istnieje = Zgloszenie.objects.filter(
				rejs=rejs,
				imie__iexact=imie,
				nazwisko__iexact=nazwisko,
				email__iexact=email,
			).exists()

			if istnieje:
				raise forms.ValidationError(
					"Na ten rejs istnieje już zgłoszenie dla tej osoby."
				)

		return cleaned

	def clean_telefon(self):
		telefon = self.cleaned_data.get("telefon", "")
		cleaned = (
			telefon.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
		)
		telefon_validator(cleaned)
		return cleaned

	def clean_kod_pocztowy(self):
		kod = self.cleaned_data.get("kod_pocztowy", "").strip()

		# normalizacja: usuń spacje
		kod = kod.replace(" ", "")

		# jeśli użytkownik wpisał 5 cyfr (np. 00123) → zamień na 00-123
		if kod.isdigit() and len(kod) == 5:
			kod = f"{kod[:2]}-{kod[2:]}"

		# walidacja właściwa
		kod_pocztowy_validator(kod)

		return kod
	
	def clean_rodo(self):
		rodo = self.cleaned_data.get("rodo")

		if rodo is not True:
			raise forms.ValidationError(
				"Aby wysłać formularz, musisz wyrazić zgodę na przetwarzanie danych osobowych."
			)

		return rodo


class Dane_DodatkoweForm(forms.ModelForm):
	class Meta:
		model = Dane_Dodatkowe
		fields = [
			"poz1",
			"poz2",
			"poz3",
			"pos4",
			"pos5",
			"pos6",
		]
		labels = {
			"poz1": "pesel",
			"poz2": "typ dokumentu",
			"poz3": "numer dokumentu",
			"pos4": "miejsce urodzenia",
			"pos5": "obywatelstwo",
			"pos6": "data ważności dokumentu",
		}
		help_texts = {
			"poz1": "podaj swój pesel",
			"poz2": "wybierz dokument który według procedur oddasz przy zaokrętowaniu się.",
			"poz3": "podaj numer dokumentu który oddasz przy zaokrętowaniu.",
			"pos4": "podaj miejsce urodzenia zgodnie z dokumentem",
			"pos5": "podaj obywatelstwo",
			"pos6": "podaj datę ważności dokumentu",
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
			"pos4": forms.TextInput(
				attrs={
					"aria-required": "true",
				}
			),
			"pos5": forms.TextInput(
				attrs={
					"aria-required": "true",
				}
			),
			"pos6": forms.DateInput(
				attrs={
					"type": "date",
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
