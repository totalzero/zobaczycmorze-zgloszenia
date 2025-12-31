"""
Sygnały Django dla aplikacji rejs.

Obsługuje zdarzenia post_save i pre_save dla modeli,
delegując logikę powiadomień do SerwisNotyfikacji.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Ogloszenie, Wplata, Zgloszenie
from .serwisy.notyfikacje import serwis_notyfikacji


@receiver(post_save, sender=Zgloszenie)
def zgloszenie_post_save(sender, instance, created, raw=False, **kwargs):
	"""Wysyła powiadomienia po zapisie zgłoszenia."""
	# Pomijamy wysyłkę emaili podczas ładowania fixtures
	if raw:
		return

	if created:
		serwis_notyfikacji.powiadom_o_utworzeniu_zgloszenia(instance)
		return

	# Sprawdzenie zmiany statusu (używamy _original_* z __init__ modelu - bez dodatkowego zapytania DB)
	original_status = getattr(instance, "_original_status", None)
	if original_status is not None and original_status != instance.status:
		serwis_notyfikacji.powiadom_o_zmianie_statusu(instance, original_status)

	# Sprawdzenie przypisania do wachty
	original_wachta_id = getattr(instance, "_original_wachta_id", None)
	if original_wachta_id is None and instance.wachta_id is not None:
		serwis_notyfikacji.powiadom_o_przypisaniu_wachty(instance)


@receiver(post_save, sender=Wplata)
def wplata_post_save(sender, instance, created, raw=False, **kwargs):
	"""Wysyła powiadomienie po utworzeniu wpłaty lub zwrotu."""
	# Pomijamy wysyłkę emaili podczas ładowania fixtures
	if raw or not created:
		return

	if instance.rodzaj == Wplata.RODZAJ_WPLATA:
		serwis_notyfikacji.powiadom_o_wplacie(instance)
	elif instance.rodzaj == Wplata.RODZAJ_ZWROT:
		serwis_notyfikacji.powiadom_o_zwrocie(instance)


@receiver(post_save, sender=Ogloszenie)
def ogloszenie_post_save(sender, instance, created, raw=False, **kwargs):
	"""Wysyła powiadomienie o nowym ogłoszeniu do wszystkich uczestników."""
	# Pomijamy wysyłkę emaili podczas ładowania fixtures
	if raw or not created:
		return

	serwis_notyfikacji.powiadom_o_ogloszeniu(instance)
