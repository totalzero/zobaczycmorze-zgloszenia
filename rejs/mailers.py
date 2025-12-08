from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

FROM = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@zobaczyc.morze")

def send_simple_mail(subject, to_mail, template_base, context):
	"""
	wysyla emaila w formacie html i txt jako fallback.
	wymaga template_base.html i/lub template_base.txt
	"""
	try:
		TXT = render_to_string(template_base + ".txt", context)
	except Exception as e:
		print(e)
		TXT = None

	try:
		HTML = render_to_string(template_base + ".html", context)
	except Exception as e:
		print(e)
		HTML = None

	print(f"zmienna TXT: {TXT}")
	print(f"zmienna HTML: {HTML}")
	email = EmailMultiAlternatives(
		subject=subject,
		body=TXT,
		from_email=FROM,
		to=[to_mail],
	)
	if HTML:
		email.attach_alternative(HTML, "text/html")
	email.send(fail_silently=False)