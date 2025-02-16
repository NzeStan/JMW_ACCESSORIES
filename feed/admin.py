from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.template.response import TemplateResponse
from .models import Image, YouTubeCache
from .youtube_service import YouTubeService
from .cache_utils import VideoCache


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("url", "upload_date", "active")
    ordering = ("-upload_date",)


@admin.register(YouTubeCache)
class YouTubeCacheAdmin(admin.ModelAdmin):
    change_list_template = "admin/feed/youtubecache/change_list.html"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return YouTubeCache.objects.none()

    def changelist_view(self, request, extra_context=None):
        cache = VideoCache()
        last_updated = cache.get_last_updated()
        videos = cache.get_cached_videos() or []

        # Get the first few video titles for display
        video_examples = []
        if videos:
            for video in videos[:5]:
                video_examples.append(
                    {
                        "id": video.get("id", "Unknown"),
                        "title": video.get("title", "Untitled"),
                    }
                )

        context = {
            "title": "YouTube Cache Management",
            "last_cache_update": last_updated,
            "videos_count": len(videos),
            "video_examples": video_examples,
            "module_name": "YouTube Cache",
            "cl": {"opts": self.model._meta},
        }

        return TemplateResponse(request, self.change_list_template, context)

    def get_urls(self):
        urls = [
            path(
                "",
                self.admin_site.admin_view(self.changelist_view),
                name="feed_youtubecache_changelist",
            ),
            path(
                "refresh-cache/",
                self.admin_site.admin_view(self.refresh_cache),
                name="refresh-youtube-cache",
            ),
        ]
        return urls

    def refresh_cache(self, request):
        try:
            youtube_service = YouTubeService()

            # Force a fresh fetch from the API
            videos = youtube_service.get_channel_videos(force_refresh=True)

            if videos:
                cache = VideoCache()
                cache.update_cache(videos)
                messages.success(
                    request,
                    f'Successfully cached {len(videos)} videos! First video: {videos[0].get("title", "Untitled")}',
                )
            else:
                messages.warning(
                    request,
                    "No videos were fetched from YouTube API. Please check your API key and channel ID.",
                )

        except Exception as e:
            messages.error(
                request,
                f"Error updating cache: {str(e)}. Please check your YouTube API configuration.",
            )

        return redirect("admin:feed_youtubecache_changelist")
