import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

FROM = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@zobaczyc.morze")


def send_simple_mail(subject, to_mail, template_base, context):
	"""
	Wysyła emaila w formacie HTML i TXT jako fallback.
	Wymaga template_base.html i/lub template_base.txt
	"""
	txt_content = None
	html_content = None

	try:
		txt_content = render_to_string(template_base + ".txt", context)
	except TemplateDoesNotExist:
		logger.warning("Nie znaleziono szablonu %s.txt", template_base)

	try:
		html_content = render_to_string(template_base + ".html", context)
	except TemplateDoesNotExist:
		logger.warning("Nie znaleziono szablonu %s.html", template_base)

	if not txt_content and not html_content:
		logger.error("Brak szablonów email dla %s - email nie zostanie wysłany", template_base)
		return

	logger.debug("Wysyłanie emaila do %s: %s", to_mail, subject)

	email = EmailMultiAlternatives(
		subject=subject,
		body=txt_content or "",
		from_email=FROM,
		to=[to_mail],
	)
	if html_content:
		email.attach_alternative(html_content, "text/html")

	try:
		email.send(fail_silently=False)
		logger.info("Email wysłany do %s: %s", to_mail, subject)
	except Exception:
		logger.exception("Błąd wysyłania emaila do %s", to_mail)
		raise
