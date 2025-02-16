from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path(
        "category/<slug:category_slug>/",
        views.product_list,
        name="product_list_by_category",
    ),
    path(
        "<str:product_type>/<uuid:id>/<slug:slug>/",
        views.product_detail,
        name="product_detail",
    ),
    path("load-more/", views.load_more_products, name="load_more"),
]
