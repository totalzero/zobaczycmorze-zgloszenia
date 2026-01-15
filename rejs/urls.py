from django.urls import path
from . import views
from .views_payu import zaplac, payu_webhook

urlpatterns = [
	path("", views.index, name="index"),
	path(
		"rejs/<int:rejs_id>/zgloszenie/",
		views.zgloszenie_utworz,
		name="zgloszenie_utworz",
	),
	path(
		"zgloszenie/<uuid:token>/",
		views.zgloszenie_details,
		name="zgloszenie_details",
	),
	path(
		"zgloszenie/<uuid:token>/dane_dodatkowe",
		views.dane_dodatkowe_form,
		name='dane_dodatkowe_form'
	)
]

urlpatterns += [
	path("payu/zaplac/<uuid:token>/<str:typ>/", zaplac, name="zaplac"),
	path("payu/webhook/", payu_webhook, name="payu_webhook"),
]
