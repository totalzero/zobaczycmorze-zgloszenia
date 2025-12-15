from django.shortcuts import render
from rejs.models import Rejs
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import RejsSerializer

class RejsViewSet(viewsets.ModelViewSet):
	queryset = Rejs.objects.all().order_by("od")
	serializer_class = RejsSerializer
	filter_backends = [DjangoFilterBackend]
	filterset_fields = ["od", "do", "start", "koniec"]

	@action(detail=True, methods=["get"])
	def zgloszenia(self, request, pk=None):
		rejs = self.get_object()
		qs = rejs.zgloszenia.all().order_by("nazwisko", "imie")
		return Response(ZgloszenieSerializer(qs, many=True).data)

	@action(detail=True, methods=["get"])
	def wachty(self, request, pk=None):
		rejs = self.get_object()
		qs = rejs.wachty.all().order_by("nazwa")
		return Response(WachtaSerializer(qs, many=True).data)

