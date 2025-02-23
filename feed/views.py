from django.views.generic import TemplateView
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Image
from .youtube_service import YouTubeService
import random
import logging

logger = logging.getLogger(__name__)


class FeedView(TemplateView):
    template_name = "feed/feed.html"
    items_per_page = 30

    def get_mixed_content(self, page_size=30, offset=0):
        youtube_service = YouTubeService()

        try:
            # Get images and prepare them with optimized URLs
            images = list(Image.objects.all()[offset : offset + page_size])
            image_content = [
                {
                    "type": "image",
                    "url": img.get_optimized_url(),
                    "upload_date": img.upload_date,
                    "active": img.active,
                }
                for img in images
            ]
        except Exception as e:
            logger.error(f"Error fetching images: {str(e)}")
            image_content = []

        try:
            # Get videos with error handling
            videos = youtube_service.get_channel_videos()[offset : offset + page_size]
            if not videos:
                logger.warning("No videos returned from YouTube API, using images only")
        except Exception as e:
            logger.error(f"Error fetching YouTube videos: {str(e)}")
            videos = []

        # Combine and shuffle only this page's content
        all_content = image_content + videos
        if not videos:
            return image_content

        random.shuffle(all_content)
        return all_content

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["content"] = self.get_mixed_content(
                page_size=self.items_per_page, offset=0
            )
        except Exception as e:
            logger.error(f"Error in get_context_data: {str(e)}")
            context["content"] = []
        return context


def load_more_content(request):
    try:
        offset = int(request.GET.get("offset", 0))
        view = FeedView()

        # Get next page of content
        content = view.get_mixed_content(page_size=view.items_per_page, offset=offset)

        if not content:
            logger.info(f"No more content at offset {offset}")
            return HttpResponse("")

        html = render_to_string(
            "feed/content_items.html", {"content": content}, request=request
        )
        return HttpResponse(html)

    except Exception as e:
        logger.error(f"Error in load_more_content: {str(e)}")
        return HttpResponse("")
