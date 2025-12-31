from decimal import Decimal

from django.db.models import Case, F, Sum, When
from django.utils.timezone import localtime

from rejs.models import Dane_Dodatkowe, Wachta, Wplata, Zgloszenie


class RaportRejsuBuilder:
	def __init__(self, rejs, user):
		self.rejs = rejs
		self.user = user

	# ---------- UPRAWNIENIA ----------
	def can_export_sensitive(self):
		return self.user.has_perm("rejs.export_sensitive_data")

	# ---------- ZAŁOGA ----------
	def build_zaloga(self):
		rows = []
		queryset = (
			Zgloszenie.objects.filter(rejs=self.rejs)
			.select_related("wachta")
			.annotate(
				wplaty_sum=Sum(
					Case(
						When(wplaty__rodzaj="wplata", then="wplaty__kwota"),
						default=Decimal("0"),
					)
				),
				zwroty_sum=Sum(
					Case(
						When(wplaty__rodzaj="zwrot", then="wplaty__kwota"),
						default=Decimal("0"),
					)
				),
			)
		)
		cena = self.rejs.cena
		for z in queryset:
			wplaty = z.wplaty_sum or Decimal("0")
			zwroty = z.zwroty_sum or Decimal("0")
			suma = wplaty - zwroty
			rows.append(
				{
					"imie": z.imie,
					"nazwisko": z.nazwisko,
					"email": z.email,
					"telefon": z.telefon,
					"data urodzenia": z.data_urodzenia,
					"adres": z.adres,
					"kod pocztowy": z.kod_pocztowy,
					"miejscowość": z.miejscowosc,
					"status": z.status,
					"wzrok": z.wzrok,
					"rola": z.rola,
					"wachta": z.wachta.nazwa if z.wachta else "",
					"suma_wplat": suma,
					"do_zaplaty": cena - suma,
				}
			)
		return rows

	# ---------- WACHTY ----------
	def build_wachty(self):
		data = []
		for w in Wachta.objects.filter(rejs=self.rejs).prefetch_related("czlonkowie"):
			members = []
			for z in w.czlonkowie.all():
				members.append(
					{
						"imie": z.imie,
						"nazwisko": z.nazwisko,
						"rola": z.rola,
					}
				)
			data.append(
				{
					"nazwa": w.nazwa,
					"czlonkowie": members,
				}
			)
		return data

	# ---------- WPŁATY ----------
	def build_wplaty(self):
		rows = []
		for w in Wplata.objects.filter(zgloszenie__rejs=self.rejs).select_related("zgloszenie").order_by("data"):
			z = w.zgloszenie
			rows.append(
				{
					"imie": z.imie,
					"nazwisko": z.nazwisko,
					"rodzaj": w.rodzaj,
					"kwota": w.kwota,
					"data": localtime(w.data).replace(tzinfo=None),
				}
			)
		return rows

	# ---------- DANE WRAŻLIWE ----------
	def build_dane_wrazliwe(self):
		if not self.can_export_sensitive():
			return None

		rows = []
		for d in Dane_Dodatkowe.objects.filter(zgloszenie__rejs=self.rejs).select_related("zgloszenie"):
			z = d.zgloszenie
			rows.append(
				{
					"imie": z.imie,
					"nazwisko": z.nazwisko,
					"pesel": d.poz1,
					"typ_dokumentu": d.poz2,
					"dokument": d.poz3,
				}
			)
		return rows
