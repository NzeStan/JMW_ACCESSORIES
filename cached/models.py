# cached/models.py
from django.db import models
from django.utils import timezone


class CacheMonitor(models.Model):
    path = models.CharField(max_length=255)
    hits = models.PositiveIntegerField(default=0)
    misses = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.path

    class Meta:
        ordering = ["-hits"]


class CacheSettings(models.Model):
    path = models.CharField(max_length=255, unique=True)
    cache_timeout = models.PositiveIntegerField(
        default=900, help_text="Cache timeout in seconds"  # 15 minutes
    )
    is_active = models.BooleanField(default=True)
    last_cleared = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.path} ({self.cache_timeout}s)"

    def clear_cache(self):
        from django.core.cache import cache

        cache.delete(self.path)
        self.last_cleared = timezone.now()
        self.save()
