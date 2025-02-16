# bulk_orders/urls.py
from django.urls import path
from . import views

app_name = "bulk_orders"

urlpatterns = [
    path("generate/", views.generate_bulk_order, name="generate"),
    path("order/<uuid:link_code>/", views.order_landing_page, name="order_landing"),
    path("copy-link/<uuid:link_id>/", views.copy_link, name="copy_link"),
    path("order/<uuid:link_code>/", views.order_landing_page, name="order_landing"),
    path("expired/", views.link_expired, name="link_expired"),
    path("toggle-coupon/", views.toggle_coupon_field, name="toggle_coupon"),
    path("order/<uuid:link_code>/submit/", views.submit_order, name="submit_order"),
    path(
        "payment/verify/<uuid:order_id>/", views.payment_verify, name="payment_verify"
    ),
    path("order/success/<uuid:order_id>/", views.order_success, name="order_success"),
    path("admin/download-pdf/<uuid:link_id>/", views.download_pdf, name="download_pdf"),
    path(
        "admin/download-word/<uuid:link_id>/", views.download_word, name="download_word"
    ),
    path(
        "admin/size-summary/<uuid:link_id>/",
        views.generate_size_summary_view,
        name="generate_size_summary",
    ),
]
