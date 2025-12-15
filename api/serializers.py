from rest_framework import serializers
from rejs.models import Rejs, Wachta, Zgloszenie, Wplata, Ogloszenie


class RejsSerializer(serializers.ModelSerializer):
	class Meta:
		model = Rejs
		fields = ["id", "nazwa", "od", "do", "start", "koniec", "cena", "zaliczka", "opis"]
