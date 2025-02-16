# pages/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver


class Testimonial(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="testimonials"
    )
    name = models.CharField(max_length=100) 
    comment = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}'s testimonial"

    def save(self, *args, **kwargs):
        # Capitalize the first letter of each word in the name
        self.name = self.name.title()
        super().save(*args, **kwargs)


class VideoMessage(models.Model):
    title = models.CharField(max_length=200)
    video = models.URLField()
    active = models.BooleanField(default=False)
