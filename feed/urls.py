from django.urls import path
from .views import FeedView, load_more_content

app_name = "feed"

urlpatterns = [
    path("", FeedView.as_view(), name="feed"),
    path("load-more/", load_more_content, name="load_more"),
]
