from django.utils.timezone import localtime
from rejs.models import Zgloszenie, Wachta, Wplata, Dane_Dodatkowe


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

		for z in (
			Zgloszenie.objects
			.filter(rejs=self.rejs)
			.select_related("wachta")
		):
			rows.append({
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
				"suma_wplat": z.suma_wplat,
				"do_zaplaty": z.do_zaplaty,
			})

		return rows

	# ---------- WACHTY ----------
	def build_wachty(self):
		data = []

		for w in (
			Wachta.objects
			.filter(rejs=self.rejs)
			.prefetch_related("czlonkowie")
		):
			members = []

			for z in w.czlonkowie.all():
				members.append({
					"imie": z.imie,
					"nazwisko": z.nazwisko,
					"rola": z.rola,
				})

			data.append({
				"nazwa": w.nazwa,
				"czlonkowie": members,
			})

		return data

	# ---------- WPŁATY ----------
	def build_wplaty(self):
		rows = []

		for w in (
			Wplata.objects
			.filter(zgloszenie__rejs=self.rejs)
			.select_related("zgloszenie")
			.order_by("data")
		):
			z = w.zgloszenie

			rows.append({
				"imie": z.imie,
				"nazwisko": z.nazwisko,
				"rodzaj": w.rodzaj,
				"kwota": w.kwota,
				"data": localtime(w.data).replace(tzinfo=None),
			})

		return rows

	# ---------- DANE WRAŻLIWE ----------
	def build_dane_wrazliwe(self):
		if not self.can_export_sensitive():
			return None

		rows = []

		for d in (
			Dane_Dodatkowe.objects
			.filter(zgloszenie__rejs=self.rejs)
			.select_related("zgloszenie")
		):
			z = d.zgloszenie

			rows.append({
				"imie": z.imie,
				"nazwisko": z.nazwisko,
				"pesel": d.poz1,
				"typ_dokumentu": d.poz2,
				"dokument": d.poz3,
			})

		return rows

	# ---------- CREW LIST (IMO FAL 5) ----------
	def build_crew_list(self):
		rows = []

		qs = (
			Zgloszenie.objects
			.filter(
				rejs=self.rejs,
				status=Zgloszenie.STATUS_ZAKWALIFIKOWANY
			)
			.select_related("dane_dodatkowe", "wachta")
			.order_by("nazwisko", "imie")
		)

		for z in qs:
			d = getattr(z, "dane_dodatkowe", None)

			rows.append({
				"family_name": z.nazwisko,
				"given_names": z.imie,
				"age": z.wiek,
				"date_of_birth": z.data_urodzenia,
				"place_of_birth": d.pos4 if d else "",
				"nationality": d.pos5 if d else "",
				"rank": z.rola,
				"document_type": d.poz2 if d else "",
				"document_number": d.poz3 if d else "",
				"document_expiry": d.pos6 if d else "",
				"sex": z.plec,
			})

		return rows
