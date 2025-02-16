# comments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CommentViewSet

app_name = "comments"

router = DefaultRouter()
router.register(r"comments", CommentViewSet, basename="comment")

urlpatterns = [
    path("", include(router.urls)),
]
