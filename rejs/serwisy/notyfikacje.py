"""
Serwis notyfikacji email.

Odpowiada za wysyłanie powiadomień email do uczestników rejsów.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.urls import reverse

from django.template.loader import render_to_string

from rejs.mailers import FROM, send_mass_mail_html, send_simple_mail
from rejs.modele.zgloszenie import Zgloszenie

if TYPE_CHECKING:
	from rejs.models import Ogloszenie, Wplata


class SerwisNotyfikacji:
	"""
	Serwis obsługujący powiadomienia email.

	Metody:
		powiadom_o_utworzeniu_zgloszenia - email po utworzeniu zgłoszenia
		powiadom_o_zmianie_statusu - email po zmianie statusu zgłoszenia
		powiadom_o_przypisaniu_wachty - email po przypisaniu do wachty
		powiadom_o_wplacie - email po zarejestrowaniu wpłaty
		powiadom_o_zwrocie - email po zarejestrowaniu zwrotu
		powiadom_o_ogloszeniu - email z nowym ogłoszeniem
	"""

	def _zbuduj_link(self, zgloszenie: Zgloszenie) -> str:
		"""Buduje pełny URL do szczegółów zgłoszenia."""
		return settings.SITE_URL + reverse("zgloszenie_details", kwargs={"token": zgloszenie.token})

	def powiadom_o_utworzeniu_zgloszenia(self, zgloszenie: Zgloszenie) -> None:
		"""
		Wysyła email potwierdzający utworzenie zgłoszenia.

		Args:
			zgloszenie: Nowo utworzone zgłoszenie
		"""
		subject = f"Potwierdzenie zgłoszenia na rejs: {zgloszenie.rejs.nazwa}"
		context = {
			"zgl": zgloszenie,
			"rejs": zgloszenie.rejs,
			"link": zgloszenie.get_absolute_url() if hasattr(zgloszenie, "get_absolute_url") else None,
		}
		send_simple_mail(subject, zgloszenie.email, "emails/zgloszenie_utworzone", context)

	def powiadom_o_zmianie_statusu(self, zgloszenie: Zgloszenie, stary_status: str) -> None:
		"""
		Wysyła email informujący o zmianie statusu zgłoszenia.

		Args:
			zgloszenie: Zgłoszenie ze zmienionym statusem
			stary_status: Poprzedni status zgłoszenia
		"""
		if stary_status == zgloszenie.status:
			return

		link = self._zbuduj_link(zgloszenie)
		context = {
			"zgl": zgloszenie,
			"old_status": stary_status,
			"new_status": zgloszenie.status,
			"link": link,
		}

		if zgloszenie.status == Zgloszenie.STATUS_ZAKWALIFIKOWANY:
			subject = f"Potwierdzamy zakwalifikowanie na rejs {zgloszenie.rejs.nazwa}"
			send_simple_mail(subject, zgloszenie.email, "emails/zgloszenie_potwierdzone", context)
		elif zgloszenie.status == Zgloszenie.STATUS_ODRZUCONE:
			subject = f"Odrzucone zgłoszenie na rejs {zgloszenie.rejs.nazwa}"
			send_simple_mail(subject, zgloszenie.email, "emails/zgloszenie_o", context)

	def powiadom_o_przypisaniu_wachty(self, zgloszenie: Zgloszenie) -> None:
		"""
		Wysyła email informujący o przypisaniu do wachty.

		Args:
			zgloszenie: Zgłoszenie przypisane do wachty
		"""
		if not zgloszenie.wachta:
			return

		subject = f"Dodano do wachty {zgloszenie.wachta.nazwa}"
		link = self._zbuduj_link(zgloszenie)
		context = {
			"zgl": zgloszenie,
			"wachta": zgloszenie.wachta,
			"link": link,
		}
		send_simple_mail(subject, zgloszenie.email, "emails/wachta_added", context)

	def powiadom_o_wplacie(self, wplata: Wplata) -> None:
		"""
		Wysyła email potwierdzający wpłatę.

		Args:
			wplata: Zarejestrowana wpłata
		"""
		zgl = wplata.zgloszenie
		link = self._zbuduj_link(zgl)
		context = {
			"zgl": zgl,
			"wplata": wplata,
			"link": link,
		}
		subject = f"Zarejestrowaliśmy nową wpłatę {zgl.imie} {zgl.nazwisko}"
		send_simple_mail(subject, zgl.email, "emails/wplata", context)

	def powiadom_o_zwrocie(self, wplata: Wplata) -> None:
		"""
		Wysyła email informujący o zwrocie.

		Args:
			wplata: Zarejestrowany zwrot
		"""
		zgl = wplata.zgloszenie
		link = self._zbuduj_link(zgl)
		context = {
			"zgl": zgl,
			"wplata": wplata,
			"link": link,
		}
		subject = f"Zwrot wpłaconych środków {zgl.imie} {zgl.nazwisko}"
		send_simple_mail(subject, zgl.email, "emails/wplata_zwrot", context)

	def powiadom_o_ogloszeniu(self, ogloszenie: Ogloszenie) -> None:
		"""
		Wysyła email z nowym ogłoszeniem do wszystkich uczestników rejsu.
		Używa batch sending dla wydajności (jedno połączenie SMTP).

		Args:
			ogloszenie: Nowe ogłoszenie
		"""
		rejs = ogloszenie.rejs
		zgloszenia = list(rejs.zgloszenia.all())

		if not zgloszenia:
			return

		subject = f"Nowe ogłoszenie dla rejsu: {rejs.nazwa}"

		# Buduj wszystkie wiadomości
		messages = []
		for zgl in zgloszenia:
			link = self._zbuduj_link(zgl)
			context = {
				"ogloszenie": ogloszenie,
				"zgl": zgl,
				"rejs": rejs,
				"link": link,
			}
			txt_content = render_to_string("emails/ogloszenie.txt", context)
			html_content = render_to_string("emails/ogloszenie.html", context)
			messages.append((subject, txt_content, html_content, FROM, [zgl.email]))

		# Wyślij wszystkie w jednym połączeniu SMTP
		send_mass_mail_html(messages)


# Domyślna instancja serwisu
serwis_notyfikacji = SerwisNotyfikacji()
