from django.db import models
from django.utils import timezone
from cloudinary_storage.storage import MediaCloudinaryStorage
import uuid


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # FIXED: Changed from URLField to ImageField with Cloudinary storage
    url = models.ImageField(
        upload_to='feed_images/',
        storage=MediaCloudinaryStorage(),
        blank=True
    )
    upload_date = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-upload_date"]

    def __str__(self):
        return f"Image {self.id} - {self.upload_date}"

    def get_optimized_url(self):
        """
        Returns optimized Cloudinary URL with transformations.
        Since we're using ImageField now, the URL is already from Cloudinary.
        """
        url_str = str(self.url)
        
        # Check if it's a Cloudinary URL
        if 'res.cloudinary.com' in url_str:
            # Check if transformations already exist
            if '/upload/' in url_str and 'c_' not in url_str:
                # Add optimization parameters
                return url_str.replace(
                    '/upload/',
                    '/upload/c_fill,f_auto,q_auto,w_800/'
                )
        
        return url_str


# Create a dummy model for YouTube cache
class YouTubeCache(models.Model):
    """Dummy model for YouTube cache admin interface"""

    class Meta:
        managed = False  # No database table creation
        verbose_name_plural = "YouTube Cache"
        app_label = "feed"