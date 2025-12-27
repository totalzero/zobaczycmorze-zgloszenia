from django.apps import AppConfig


class RejsConfig(AppConfig):
	default_auto_field = "django.db.models.BigAutoField"
	name = "rejs"

	def ready(self):
		import rejs.signals
