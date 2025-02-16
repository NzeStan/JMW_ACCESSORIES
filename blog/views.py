from django.db.models import F
from django.views.generic import DetailView
from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from .models import Post
from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from cached.decorators import monitored_cache_page


@method_decorator(monitored_cache_page, name="dispatch")
class PostListView(ListView):
    model = Post
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 10  # Shows 10 posts per page

    def get_queryset(self):
        """
        Override get_queryset to show only published posts
        ordered by published date
        """
        return Post.objects.filter(status="published").order_by("-published_date")

    def get_context_data(self, **kwargs):
        """
        Add extra context data to the template
        """
        context = super().get_context_data(**kwargs)
        context["title"] = "Blog Posts"
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = "blog/post_detail.html"
    context_object_name = "post"
    query_pk_and_slug = True

    def get_object(self, queryset=None):
        # Get the post object
        obj = super().get_object(queryset=queryset)

        # Increment the view count atomically to prevent race conditions
        Post.objects.filter(id=obj.id).update(view_count=F("view_count") + 1)

        if self.request.user.is_staff:
            return obj
        return get_object_or_404(Post, id=obj.id, status="published")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object

        # Get content type for comments system
        content_type = ContentType.objects.get_for_model(Post).model

        # Add all necessary context
        context.update(
            {
                "title": post.title,
                "related_posts": post.get_related_posts(),
                "trending_posts": Post.get_trending_posts(),
                # Add these for the comment system
                "content_type": content_type,
                "object_id": str(post.id),  # Convert to string in case it's UUID
            }
        )

        return context
