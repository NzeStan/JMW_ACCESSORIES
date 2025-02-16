from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="cart_detail"),
    path("add/<str:product_type>/<uuid:product_id>/", views.cart_add, name="cart_add"),
    path(
        "remove/<str:product_type>/<uuid:product_id>/",
        views.cart_remove,
        name="cart_remove",
    ),
    # Add this new URL pattern for clearing the cart
    path("clear/", views.cart_clear, name="cart_clear"),
    path(
        "update/<str:product_type>/<uuid:product_id>/",
        views.update_quantity,
        name="update_quantity",
    ),
    path("summary/", views.cart_summary, name="cart_summary"),
]
