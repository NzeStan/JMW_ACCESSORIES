from django.db import models
from django.utils import timezone
import uuid


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=500)
    upload_date = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-upload_date"]

    def __str__(self):
        return f"Image {self.id} - {self.upload_date}"


# Create a dummy model for YouTube cache
class YouTubeCache(models.Model):
    """Dummy model for YouTube cache admin interface"""

    class Meta:
        managed = False  # No database table creation
        verbose_name_plural = "YouTube Cache"
        app_label = "feed"
