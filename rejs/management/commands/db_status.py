"""Management command to display database status after reset."""

from django.core.management.base import BaseCommand

from rejs.models import Ogloszenie, Rejs, Wachta, Wplata, Zgloszenie


def polish_plural(count: int, singular: str, plural_2_4: str, plural_5_plus: str) -> str:
	"""Return proper Polish plural form based on count."""
	if count == 1:
		return f"{count} {singular}"
	elif 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
		return f"{count} {plural_2_4}"
	else:
		return f"{count} {plural_5_plus}"


class Command(BaseCommand):
	"""Display database status and remind about createsuperuser."""

	help = "Wyswietla status bazy danych po resecie"

	def handle(self, *args, **options):
		# Count objects
		rejsy = Rejs.objects.count()
		zgloszenia = Zgloszenie.objects.count()
		wachty = Wachta.objects.count()
		wplaty = Wplata.objects.count()
		ogloszenia = Ogloszenie.objects.count()

		total = rejsy + zgloszenia + wachty + wplaty + ogloszenia

		self.stdout.write("")
		self.stdout.write(self.style.SUCCESS("Baza danych gotowa."))

		if total > 0:
			# Format counts with proper Polish plurals
			parts = []
			if rejsy:
				parts.append(polish_plural(rejsy, "rejs", "rejsy", "rejsow"))
			if zgloszenia:
				parts.append(polish_plural(zgloszenia, "zgloszenie", "zgloszenia", "zgloszen"))
			if wachty:
				parts.append(polish_plural(wachty, "wachta", "wachty", "wacht"))
			if wplaty:
				parts.append(polish_plural(wplaty, "wplata", "wplaty", "wplat"))
			if ogloszenia:
				parts.append(polish_plural(ogloszenia, "ogloszenie", "ogloszenia", "ogloszen"))

			self.stdout.write(f"Zaladowano: {', '.join(parts)}")
		else:
			self.stdout.write("Baza jest pusta (brak danych testowych).")

		self.stdout.write("")
		self.stdout.write("Nastepny krok: Uruchom 'poe createsuperuser' aby utworzyc konto administratora.")
		self.stdout.write("")
