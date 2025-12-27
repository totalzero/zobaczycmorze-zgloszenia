"""
Moduł audytu dostępu do danych wrażliwych.

Loguje operacje na danych osobowych (PESEL, dokumenty) zgodnie z wymogami RODO.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from django.http import HttpRequest

	from .models import AuditLog


def log_audit(
	request: HttpRequest | None,
	akcja: str,
	model_name: str,
	object_id: int | None = None,
	object_repr: str = "",
	szczegoly: str = "",
) -> AuditLog:
	"""
	Tworzy wpis w logu audytu.

	Args:
	    request: Obiekt HttpRequest (może być None dla operacji systemowych)
	    akcja: Jedna z wartości AKCJA_CHOICES ("odczyt", "utworzenie", "modyfikacja", "usuniecie", "eksport")
	    model_name: Nazwa modelu (np. "Dane_Dodatkowe")
	    object_id: ID obiektu
	    object_repr: Tekstowa reprezentacja obiektu
	    szczegoly: Dodatkowe szczegóły operacji

	Returns:
	    Utworzony obiekt AuditLog
	"""
	from .models import AuditLog

	ip_address = None
	user_agent = ""
	uzytkownik = None

	if request:
		x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
		if x_forwarded_for:
			ip_address = x_forwarded_for.split(",")[0].strip()
		else:
			ip_address = request.META.get("REMOTE_ADDR")

		user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

		if hasattr(request, "user") and request.user.is_authenticated:
			uzytkownik = request.user

	return AuditLog.objects.create(
		uzytkownik=uzytkownik,
		akcja=akcja,
		model_name=model_name,
		object_id=object_id,
		object_repr=object_repr[:200] if object_repr else "",
		ip_address=ip_address,
		user_agent=user_agent,
		szczegoly=szczegoly,
	)
