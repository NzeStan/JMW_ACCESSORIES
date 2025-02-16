from django.urls import path
from . import views

app_name = "payment"

urlpatterns = [
    path("initiate/", views.InitiatePaymentView.as_view(), name="initiate"),
    path("verify/", views.verify_payment_view, name="verify_payment"),
    path("success/", views.payment_success, name="success"),
    path("failed/", views.payment_failed, name="failed"),
]
