from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BulkOrderLinkViewSet, OrderEntryViewSet, CouponCodeViewSet

app_name = "bulk_orders"

router = DefaultRouter()
router.register(r'links', BulkOrderLinkViewSet, basename='bulk-link')
router.register(r'orders', OrderEntryViewSet, basename='bulk-order')
router.register(r'coupons', CouponCodeViewSet, basename='bulk-coupon')

urlpatterns = [
    path('', include(router.urls)),
]
