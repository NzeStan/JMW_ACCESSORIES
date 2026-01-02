from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ImageViewSet, YouTubeVideoView

app_name = "feed"

router = DefaultRouter()
router.register(r'images', ImageViewSet, basename='image')

urlpatterns = [
    path('youtube/', YouTubeVideoView.as_view(), name='youtube-videos'),
    path('', include(router.urls)),
]
