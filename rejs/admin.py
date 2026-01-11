from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from django.http import HttpResponse
from rejs.reports import generate_rejs_report
from .models import Ogloszenie, Rejs, Wachta, Wplata, Zgloszenie, Dane_Dodatkowe


@admin.action(description="Generuj raport Excel dla rejsu")
def generate_report(modeladmin, request, queryset):
	if queryset.count() != 1:
		modeladmin.message_user(
			request,
			"Wybierz dokładnie jeden rejs.",
			level="error"
		)
		return

	rejs = queryset.first()
	return generate_rejs_report(rejs, request.user)


class OgloszenieInline(admin.StackedInline):
	model = Ogloszenie
	extra = 0
	fields = ("tytul", "text")


class WachtaForm(forms.ModelForm):
	czlonkowie = forms.ModelMultipleChoiceField(
		Zgloszenie.objects.none(),
		required=False,
		widget=widgets.FilteredSelectMultiple("Członkowie", is_stacked=False),
	)

	class Meta:
		model = Wachta
		fields = "__all__"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		if self.instance and self.instance.pk:
			self.fields["czlonkowie"].queryset = Zgloszenie.objects.filter(
				rejs=self.instance.rejs,
				wachta=None
			)
			self.fields["czlonkowie"].initial = self.instance.czlonkowie.all()
		else:
			rejs_initial = self.initial.get("rejs") or (
				self.data.get("rejs") if self.data else None
			)
			if rejs_initial:
				try:
					self.fields["czlonkowie"].queryset = Zgloszenie.objects.filter(
						rejs_id=rejs_initial
					)
				except Exception:
					self.fields["czlonkowie"].queryset = Zgloszenie.objects.none()
			else:
				self.fields["czlonkowie"].queryset = Zgloszenie.objects.none()

	def save(self, commit=True):
		instance = super().save(commit=commit)
		selected = self.cleaned_data.get("czlonkowie", [])
		current = set(self.instance.czlonkowie.all())
		to_remove = current - set(selected)
		for zg in to_remove:
			zg.wachta = None
			zg.save(update_fields=["wachta"])

		for zg in selected:
			if zg.rejs_id != instance.rejs_id:
				raise forms.ValidationError(
					f"Zgłoszenie {zg} nie należy do rejsu {instance.rejs}"
				)
			zg.wachta = instance
			zg.save(update_fields=["wachta"])
		return instance


class WachtaAdmin(admin.ModelAdmin):
	form = WachtaForm
	list_display = ("nazwa", "rejs")
	list_filter = ("rejs",)


class WachtaInline(admin.TabularInline):
	model = Wachta
	form = WachtaForm
	extra = 0
	show_change_link = True


class WplataInline(admin.TabularInline):
	model = Wplata
	extra = 0
	readonly_fields = ["data"]
	ordering = ["data"]


class ZgloszenieInline(admin.TabularInline):
	model = Zgloszenie
	extra = 0
	#readonly_fields = ["imie", "nazwisko", "email", "telefon"]
	show_change_link = True


@admin.register(Rejs)
class RejsyAdmin(admin.ModelAdmin):
	list_display = ["nazwa", "od", "do", "start", "koniec"]
	actions = [generate_report]
	inlines = [ZgloszenieInline, WachtaInline, OgloszenieInline]


@admin.register(Zgloszenie)
class ZgloszenieAdmin(admin.ModelAdmin):
	list_display = [field.name for field in Zgloszenie._meta.fields]
	list_filter = ("rejs",)
	search_fields = ("imie", "nazwisko")
	readonly_fields = ("rejs_cena", "do_zaplaty", "suma_wplat")
	inlines = [WplataInline]
	fieldsets = (
		(
			"Dane zgłoszenia:",
			{
				"fields": (
					"imie",
					"nazwisko",
					"email",
					"telefon",
					"status",
					"wzrok",
					"rejs",
					"wachta",
				)
			},
		),
		(
			"Rozliczenie:",
			{"fields": ("rejs_cena", "suma_wplat", "do_zaplaty")},
		),
	)

@admin.register(Dane_Dodatkowe)
class Dane_DodatkoweAdmin(admin.ModelAdmin):
	list_display = ('zgloszenie', 'poz1', 'poz2', 'poz3')