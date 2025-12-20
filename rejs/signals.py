from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse

from .mailers import send_simple_mail
from .models import Ogloszenie, Wplata, Zgloszenie


@receiver(pre_save, sender=Zgloszenie)
def zgloszenie_pre_save(sender, instance, **kwargs):
	if not instance.pk:
		instance._old_status = None
		instance._old_wachta_id = None
	else:
		try:
			old = Zgloszenie.objects.get(pk=instance.pk)
			instance._old_status = old.status
			instance._old_wachta_id = old.wachta_id
		except Zgloszenie.DoesNotExist:
			instance._old_status = None
			instance._old_wachta_id = None


@receiver(post_save, sender=Zgloszenie)
def zgloszenie_post_save(sender, instance, created, **kwargs):
	if created:
		subject = f"Potwierdzenie zgłoszenia na rejs: {instance.rejs.nazwa}"
		context = {
			"zgl": instance,
			"rejs": instance.rejs,
			"link": instance.get_absolute_url()
			if hasattr(instance, "get_absolute_url")
			else None,
		}
		send_simple_mail(
			subject, instance.email, "emails/zgloszenie_utworzone", context
		)
		return

	old_status = getattr(instance, "_old_status", None)
	if old_status is not None and old_status != instance.status:
		link = settings.SITE_URL + reverse(
			"zgloszenie_details", kwargs={"token": instance.token}
		)
		context = {
			"zgl": instance,
			"old_status": old_status,
			"new_status": instance.status,
			"link": link,
		}

		if instance.status == "QUALIFIED":
			subject = f"Potwierdzamy zakwalifikowanie na rejs {instance.rejs.nazwa}"
			send_simple_mail(
				subject, instance.email, "emails/zgloszenie_potwierdzone", context
			)
		elif instance.status == "ODRZUCONE":
			subject = f"Odrzucone zgłoszenie na rejs {instance.rejs.nazwa}"
			send_simple_mail(subject, instance.email, "emails/zgloszenie_o", context)

	old_wachta_id = getattr(instance, "_old_wachta_id", None)
	if old_wachta_id is None and instance.wachta_id is not None:
		subject = f"Dodano do wachty {instance.wachta.nazwa}"
		link = settings.SITE_URL + reverse(
			"zgloszenie_details", kwargs={"token": instance.token}
		)
		context = {
			"zgl": instance,
			"wachta": instance.wachta,
			"link": link,
		}
		send_simple_mail(subject, instance.email, "emails/wachta_added", context)


@receiver(post_save, sender=Wplata)
def wplata_post_save(sender, instance, created, **kwargs):
	if not created:
		return
	zgl = instance.zgloszenie
	link = settings.SITE_URL + reverse(
		"zgloszenie_details", kwargs={"token": zgl.token}
	)
	context = {
		"zgl": zgl,
		"wplata": instance,
		"link": link,
	}
	if instance.rodzaj == "wplata":
		subject = f"Zarejestrowaliśmy nową wpłatę {zgl.imie} {zgl.nazwisko}"
		send_simple_mail(subject, zgl.email, "emails/wplata", context)
	elif instance.rodzaj == "zwrot":
		subject = f"Zwrot wpłaconych środków {zgl.imie} {zgl.nazwisko}"
		send_simple_mail(subject, zgl.email, "emails/wplata_zwrot", context)


@receiver(post_save, sender=Ogloszenie)
def ogloszenie_post_save(sender, instance, created, **kwargs):
	if not created:
		return
	rejs = instance.rejs
	zgloszenia = rejs.zgloszenia.all()
	for z in zgloszenia:
		subject = f"Nowe ogłoszenie dla rejsu: {rejs.nazwa}"
		link = settings.SITE_URL + reverse(
			"zgloszenie_details", kwargs={"token": z.token}
		)
		context = {
			"ogloszenie": instance,
			"zgl": z,
			"rejs": rejs,
			"link": link,
		}
		send_simple_mail(subject, z.email, "emails/ogloszenie", context)
