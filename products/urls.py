from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, NyscKitViewSet, NyscTourViewSet, ChurchViewSet

app_name = "products"

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'nysc-kits', NyscKitViewSet)
router.register(r'nysc-tours', NyscTourViewSet)
router.register(r'church-items', ChurchViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
