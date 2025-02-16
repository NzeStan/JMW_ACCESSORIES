from django.urls import path
from . import views

urlpatterns = [
    path("", views.router_webhook, name="webhook"),
]
