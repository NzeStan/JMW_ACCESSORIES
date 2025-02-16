from django.urls import path
from . import views

app_name = "pages"

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
    path("about/", views.AboutPageView.as_view(), name="about"),
    path("contact/", views.ContactPageView.as_view(), name="contact"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("testimonials/create/", views.create_testimonial, name="create_testimonial"),
    path(
        "testimonials/<int:pk>/edit/", views.edit_testimonial, name="edit_testimonial"
    ),
    path(
        "testimonials/<int:pk>/delete/",
        views.delete_testimonial,
        name="delete_testimonial",
    ),
    path("testimonials/toggle/", views.toggle_testimonials, name="toggle_testimonials"),
]
