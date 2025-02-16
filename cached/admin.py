# cached/admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.core.cache import cache
from django.contrib import messages
from .models import CacheMonitor, CacheSettings


@admin.register(CacheMonitor)
class CacheMonitorAdmin(admin.ModelAdmin):
    list_display = ["path", "hits", "misses", "hit_rate", "last_accessed"]
    readonly_fields = ["hits", "misses", "last_accessed", "created_at"]
    search_fields = ["path"]

    def hit_rate(self, obj):
        total = obj.hits + obj.misses
        if total == 0:
            return "0%"
        return f"{(obj.hits / total) * 100:.1f}%"

    hit_rate.short_description = "Hit Rate"


@admin.register(CacheSettings)
class CacheSettingsAdmin(admin.ModelAdmin):
    list_display = ["path", "cache_timeout", "is_active", "last_cleared"]
    list_editable = ["cache_timeout", "is_active"]
    search_fields = ["path"]
    actions = ["clear_cache"]

    def clear_cache(self, request, queryset):
        for settings in queryset:
            settings.clear_cache()
        messages.success(request, f"Cleared cache for {queryset.count()} paths")

    clear_cache.short_description = "Clear cache for selected paths"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("clear-all/", self.clear_all_cache, name="clear-all-cache"),
        ]
        return custom_urls + urls

    def clear_all_cache(self, request):
        cache.clear()
        messages.success(request, "Cleared all cache")
        return redirect("..")
