# email_tracking/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="email_dashboard"),
    path("sns/endpoint/", views.sns_endpoint, name="sns_endpoint"),
]
