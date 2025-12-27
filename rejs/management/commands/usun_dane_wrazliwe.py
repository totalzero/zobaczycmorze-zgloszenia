"""
Komenda Django do automatycznego usuwania danych wrazliwych po zakonczeniu rejsu.

Zgodnie z polityka retencji danych (RODO), dane wrazliwe (PESEL, dokumenty)
sa usuwane 30 dni po zakonczeniu rejsu.

Uzycie:
    python manage.py usun_dane_wrazliwe
    python manage.py usun_dane_wrazliwe --dry-run  # tylko podglad
    python manage.py usun_dane_wrazliwe --dni 60   # zmiana okresu retencji

Zalecane uruchamianie przez cron/scheduler raz dziennie.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from rejs.models import AuditLog, Dane_Dodatkowe


class Command(BaseCommand):
	help = "Usuwa dane wrazliwe (PESEL, dokumenty) dla rejsow zakonczonych ponad 30 dni temu"

	def add_arguments(self, parser):
		parser.add_argument(
			"--dry-run",
			action="store_true",
			help="Tylko wyswietl co zostaloby usuniete, bez faktycznego usuwania",
		)
		parser.add_argument(
			"--dni",
			type=int,
			default=30,
			help="Liczba dni po zakonczeniu rejsu, po ktorych dane sa usuwane (domyslnie: 30)",
		)

	def handle(self, *args, **options):
		dry_run = options["dry_run"]
		dni_retencji = options["dni"]

		data_graniczna = timezone.now().date() - timedelta(days=dni_retencji)

		dane_do_usuniecia = Dane_Dodatkowe.objects.filter(zgloszenie__rejs__do__lt=data_graniczna).select_related(
			"zgloszenie", "zgloszenie__rejs"
		)

		liczba = dane_do_usuniecia.count()

		if liczba == 0:
			self.stdout.write(self.style.SUCCESS("Brak danych wrazliwych do usuniecia."))
			return

		self.stdout.write(
			f"Znaleziono {liczba} rekordow danych wrazliwych do usuniecia (rejsy zakonczone przed {data_graniczna}):"
		)

		for dane in dane_do_usuniecia:
			zgloszenie = dane.zgloszenie
			rejs = zgloszenie.rejs
			self.stdout.write(
				f"  - {zgloszenie.imie} {zgloszenie.nazwisko} (rejs: {rejs.nazwa}, zakonczony: {rejs.do})"
			)

		if dry_run:
			self.stdout.write(
				self.style.WARNING(f"\n[DRY-RUN] Zadne dane nie zostaly usuniete. Uruchom bez --dry-run aby usunac.")
			)
			return

		for dane in dane_do_usuniecia:
			zgloszenie = dane.zgloszenie
			AuditLog.objects.create(
				uzytkownik=None,
				akcja="usuniecie",
				model_name="Dane_Dodatkowe",
				object_id=dane.pk,
				object_repr=f"Dane dla: {zgloszenie.imie} {zgloszenie.nazwisko}",
				szczegoly=f"Automatyczne usuniecie po {dni_retencji} dniach od zakonczenia rejsu. "
				f"Rejs: {zgloszenie.rejs.nazwa}, zakonczony: {zgloszenie.rejs.do}",
			)

		usuniete, _ = dane_do_usuniecia.delete()

		self.stdout.write(self.style.SUCCESS(f"\nUsunieto {usuniete} rekordow danych wrazliwych."))
