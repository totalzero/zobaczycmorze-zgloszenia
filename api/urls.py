from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RejsViewSet

router = DefaultRouter()
router.register(r"rejsy", RejsViewSet, basename="rejs")

urlpatterns = [
    path("", include(router.urls)),
]
