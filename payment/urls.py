from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InitializePaymentView, VerifyPaymentView, PaymentTransactionViewSet

app_name = "payment"

router = DefaultRouter()
router.register(r'transactions', PaymentTransactionViewSet, basename='transaction')

urlpatterns = [
    path('initialize/', InitializePaymentView.as_view(), name='initialize'),
    path('verify/', VerifyPaymentView.as_view(), name='verify'),
    path('', include(router.urls)),
]
