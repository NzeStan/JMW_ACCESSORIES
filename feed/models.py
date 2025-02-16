from django.db import models
from django.utils import timezone
import uuid
from cloudinary_storage.storage import MediaCloudinaryStorage


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=500)
    upload_date = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-upload_date"]

    def get_optimized_url(self):
        """Returns an optimized URL, handling both uploaded and external URLs"""
        if "cloudinary.com" in self.url:
            # Handle Cloudinary URLs (both uploaded and external)
            if "/upload/" in self.url:
                base_url, image_path = self.url.split("/upload/")
                # Add optimization parameters while preserving any existing transformations
                if "c_" not in image_path and "f_" not in image_path:
                    return f"{base_url}/upload/c_fill,f_auto,q_auto/{image_path}"
            return self.url
        return self.url

    def save(self, *args, **kwargs):
        # This will be useful when you add file upload functionality
        # It ensures the URL is properly formatted before saving
        if self.url and "cloudinary.com" in self.url:
            # Clean up any duplicate transformation parameters
            if "/upload/c_fill,f_auto,q_auto/" in self.url:
                base_url, image_path = self.url.split("/upload/")
                if "c_fill,f_auto,q_auto/" in image_path:
                    image_path = image_path.replace("c_fill,f_auto,q_auto/", "")
                self.url = f"{base_url}/upload/{image_path}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image {self.id} - {self.upload_date}"


# Create a dummy model for YouTube cache
class YouTubeCache(models.Model):
    """Dummy model for YouTube cache admin interface"""

    class Meta:
        managed = False  # No database table creation
        verbose_name_plural = "YouTube Cache"
        app_label = "feed"
