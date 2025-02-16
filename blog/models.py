from django.db import models
from django.urls import reverse
import uuid
from django.db.models import Count
from django.utils import timezone
from cloudinary_storage.storage import MediaCloudinaryStorage

class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=800)
    author = models.CharField(
        max_length=20, default="JMW & ACCESSORIES", verbose_name="Author"
    )
    author_image = models.URLField(
        max_length=600,
        blank=True,
        default="https://res.cloudinary.com/dhhaiy58r/image/upload/v1721420288/Black_White_Minimalist_Clothes_Store_Logo_e1o8ow.png",
    )
    slug = models.SlugField(max_length=200, unique=True)
    image = models.ImageField(
        upload_to="blog_images/", storage=MediaCloudinaryStorage(), blank=True
    )
    content = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    published_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=[("draft", "Draft"), ("published", "Published")],
        default="draft",
    )
    view_count = models.PositiveIntegerField(default=0)

    @classmethod
    def get_trending_posts(cls, days=7, count=3):
        """
        Returns posts with the highest view counts in the last N days.
        This helps identify what's currently popular.
        """
        date_threshold = timezone.now() - timezone.timedelta(days=days)
        return cls.objects.filter(
            status="published", published_date__gte=date_threshold
        ).order_by("-view_count")[:count]

    def get_related_posts(self, count=3):
        """
        Returns posts that might be interesting to readers of this post.
        Currently uses a simple algorithm based on creation date,
        but  could be enhanced this with tags or categories later.
        """
        return (
            Post.objects.filter(status="published")
            .exclude(id=self.id)
            .order_by("-published_date")[:count]
        )

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog:post_detail", args=[self.id, self.slug])

    def save(self, *args, **kwargs):
        # If the post is being published for the first time
        if self.status == "published" and self.published_date is None:
            self.published_date = timezone.now()
        # If the post is being unpublished
        elif self.status == "draft" and self.published_date is not None:
            self.published_date = None
        super().save(*args, **kwargs)
