"""
Modele związane z finansami (wpłaty, zwroty).
"""

from django.db import models

from rejs.modele.zgloszenie import Zgloszenie


class Wplata(models.Model):
	rodzaje = [("wplata", "Wpłata"), ("zwrot", "Zwrot")]
	kwota = models.DecimalField(default=0, blank=False, null=False, max_digits=10, decimal_places=2)
	data = models.DateTimeField(auto_now_add=True)
	rodzaj = models.CharField(max_length=7, default=rodzaje[0][0], choices=rodzaje)
	zgloszenie = models.ForeignKey(
		Zgloszenie,
		related_name="wplaty",
		on_delete=models.CASCADE,
		blank=True,
		null=True,
	)

	class Meta:
		app_label = "rejs"
		verbose_name = "Wpłata"
		verbose_name_plural = "Wpłaty"

	def __str__(self):
		return f"Wpłata: {self.kwota} zł"
