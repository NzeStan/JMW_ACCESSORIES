from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MeasurementViewSet

app_name = "measurement"

router = DefaultRouter()
router.register(r'measurements', MeasurementViewSet, basename='measurement')

urlpatterns = [
    path('', include(router.urls)),
]
