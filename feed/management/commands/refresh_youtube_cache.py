# feed/management/commands/refresh_youtube_cache.py
from django.core.management.base import BaseCommand
from feed.youtube_service import YouTubeService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Refreshes the YouTube video cache"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear the cache before refreshing",
        )

    def handle(self, *args, **kwargs):
        service = YouTubeService()

        if kwargs["clear"]:
            self.stdout.write("Clearing existing cache...")
            service.cache.update_cache([])  # Clear the cache

        self.stdout.write("Fetching videos from YouTube...")
        videos = service.get_channel_videos(force_refresh=True)

        if videos:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully cached {len(videos)} videos")
            )
            # Print first few video titles for verification
            self.stdout.write("\nFirst few videos cached:")
            for video in videos[:5]:
                self.stdout.write(f"- {video.get('title', 'Untitled')} ({video['id']})")
        else:
            self.stdout.write(self.style.WARNING("No videos were cached"))
