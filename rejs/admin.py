from django import forms
from django.contrib import admin
from django.contrib.admin import widgets
from django.http import HttpResponse

from rejs.reports import generate_rejs_report

from .audit import log_audit
from .models import (
	AuditLog,
	Dane_Dodatkowe,
	Ogloszenie,
	Rejs,
	Wachta,
	Wplata,
	Zgloszenie,
)


@admin.action(description="Generuj raport Excel dla rejsu")
def generate_report(modeladmin, request, queryset):
	if queryset.count() != 1:
		modeladmin.message_user(
			request,
			"Wybierz dokładnie jeden rejs.",
			level="error",
		)
		return

	rejs = queryset.first()
	# Log audit for report generation with sensitive data
	log_audit(
		request=request,
		akcja="eksport",
		model_name="Rejs",
		object_id=rejs.id,
		object_repr=str(rejs),
		szczegoly="Wygenerowano raport Excel z danymi rejsu",
	)
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
			self.fields["czlonkowie"].queryset = Zgloszenie.objects.filter(rejs=self.instance.rejs)
			self.fields["czlonkowie"].initial = self.instance.czlonkowie.all()
		else:
			rejs_initial = self.initial.get("rejs") or (self.data.get("rejs") if self.data else None)
			if rejs_initial:
				try:
					self.fields["czlonkowie"].queryset = Zgloszenie.objects.filter(rejs_id=rejs_initial)
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
				raise forms.ValidationError(f"Zgłoszenie {zg} nie należy do rejsu {instance.rejs}")
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
	# readonly_fields = ["imie", "nazwisko", "email", "telefon"]
	show_change_link = True


@admin.register(Rejs)
class RejsyAdmin(admin.ModelAdmin):
	list_display = ["nazwa", "od", "do", "start", "koniec"]
	actions = [generate_report]
	inlines = [ZgloszenieInline, WachtaInline, OgloszenieInline]


@admin.register(Zgloszenie)
class ZgloszenieAdmin(admin.ModelAdmin):
	list_display = ("id", "imie", "nazwisko", "rejs")
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
	list_display = (
		"zgloszenie",
		"masked_pesel_display",
		"poz2",
		"masked_dokument_display",
	)
	readonly_fields = ("zgloszenie",)

	@admin.display(description="PESEL (zamaskowany)")
	def masked_pesel_display(self, obj):
		return obj.masked_pesel

	@admin.display(description="Nr dokumentu (zamaskowany)")
	def masked_dokument_display(self, obj):
		return obj.masked_dokument

	def change_view(self, request, object_id, form_url="", extra_context=None):
		log_audit(
			request=request,
			akcja="odczyt",
			model_name="Dane_Dodatkowe",
			object_id=int(object_id),
			szczegoly="Podgląd danych wrażliwych w panelu admina",
		)
		return super().change_view(request, object_id, form_url, extra_context)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
	list_display = (
		"timestamp",
		"uzytkownik",
		"akcja",
		"model_name",
		"object_repr",
		"ip_address",
	)
	list_filter = ("akcja", "model_name", "uzytkownik")
	search_fields = ("object_repr", "szczegoly", "ip_address")
	readonly_fields = (
		"timestamp",
		"uzytkownik",
		"akcja",
		"model_name",
		"object_id",
		"object_repr",
		"ip_address",
		"user_agent",
		"szczegoly",
	)
	date_hierarchy = "timestamp"
	ordering = ["-timestamp"]

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return request.user.is_superuser
