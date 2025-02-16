from django.urls import path
from .views import PostListView, PostDetailView
from .feeds import BlogFeed, AtomBlogFeed

app_name = "blog"  # This sets up the namespace for your URLs

urlpatterns = [
    path("", PostListView.as_view(), name="post_list"),
    path("post/<uuid:id>/<slug:slug>/", PostDetailView.as_view(), name="post_detail"),
    # RSS feed
    path("feed/rss/", BlogFeed(), name="post_feed_rss"),
    # Atom feed
    path("feed/atom/", AtomBlogFeed(), name="post_feed_atom"),
]
