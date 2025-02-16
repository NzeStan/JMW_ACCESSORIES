# feed/tests.py

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from .models import Image
from .youtube_service import YouTubeService
import logging

logger = logging.getLogger(__name__)


class FeedTests(TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.client = Client()

        # Create test images
        self.regular_image = Image.objects.create(
            url="https://example.com/test1.jpg", upload_date=timezone.now()
        )

        self.cloudinary_image = Image.objects.create(
            url="https://res.cloudinary.com/dhhaiy58r/image/upload/v1685717651/test/image.jpg",
            upload_date=timezone.now(),
        )

    def test_feed_view_basic_load(self):
        """Test that the feed view loads successfully"""
        response = self.client.get(reverse("feed:feed"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "feed/feed.html")

    def test_feed_view_contains_images(self):
        """Test that the feed view contains the images in their correct format"""
        response = self.client.get(reverse("feed:feed"))

        # For regular image, the URL should remain unchanged
        self.assertContains(response, self.regular_image.url)

        # For Cloudinary image, we need to check for both possible formats
        # Either the original URL or the optimized version could be present
        cloudinary_url_found = (
            self.cloudinary_image.url in response.content.decode()
            or "c_fill,f_auto,q_auto" in response.content.decode()
        )
        self.assertTrue(
            cloudinary_url_found,
            "Neither original nor optimized Cloudinary URL found in response",
        )

    def test_image_optimization(self):
        """Test that Cloudinary URLs are properly optimized"""
        # Regular image URL should remain unchanged
        self.assertEqual(self.regular_image.get_optimized_url(), self.regular_image.url)

        # Cloudinary URL should be optimized
        optimized_url = self.cloudinary_image.get_optimized_url()
        self.assertIn("c_fill,f_auto,q_auto", optimized_url)

    def test_feed_pagination(self):
        """Test that feed pagination works correctly"""
        # Create enough images for pagination
        for i in range(15):
            Image.objects.create(
                url=f"https://example.com/test{i+2}.jpg", upload_date=timezone.now()
            )

        # Test first page
        response = self.client.get(reverse("feed:feed"))
        self.assertEqual(response.status_code, 200)

        # Test load more endpoint
        response = self.client.get(
            reverse("feed:load_more"),
            {"offset": "10"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "feed/content_items.html")

    @patch("feed.youtube_service.YouTubeService.get_channel_videos")
    def test_mixed_content_feed(self, mock_get_videos):
        """Test that feed properly mixes images and videos"""
        # Mock YouTube video response
        mock_videos = [
            {"id": "test123", "upload_date": "2024-01-01T00:00:00Z", "type": "video"}
        ]
        mock_get_videos.return_value = mock_videos

        response = self.client.get(reverse("feed:feed"))
        content = response.content.decode()

        # Check for both image and video content
        self.assertIn("youtube-player", content)
        self.assertIn("img", content)

    def test_error_handling(self):
        """Test error handling in the feed view"""
        # Create an invalid image URL
        invalid_image = Image.objects.create(
            url="https://invalid-url.com/image.jpg", upload_date=timezone.now()
        )

        response = self.client.get(reverse("feed:feed"))
        self.assertEqual(response.status_code, 200)  # Should still render

        # Verify error handling script is present
        self.assertIn("handleImageError", response.content.decode())

    def test_cloudinary_url_handling(self):
        """Test various Cloudinary URL scenarios"""
        # Test URL with existing transformations
        image_with_transforms = Image.objects.create(
            url="https://res.cloudinary.com/dhhaiy58r/image/upload/c_scale,w_500/test/image.jpg",
            upload_date=timezone.now(),
        )

        # Should not add optimization parameters to already transformed URL
        self.assertEqual(
            image_with_transforms.get_optimized_url(), image_with_transforms.url
        )

    @patch("feed.youtube_service.YouTubeService.get_channel_videos")
    def test_youtube_integration(self, mock_get_videos):
        """Test YouTube video integration"""
        mock_videos = [
            {"id": "video123", "upload_date": "2024-01-01T00:00:00Z", "type": "video"}
        ]
        mock_get_videos.return_value = mock_videos

        response = self.client.get(reverse("feed:feed"))
        content = response.content.decode()

        # Check for YouTube player initialization
        self.assertIn("youtube-player", content)
        self.assertIn("data-video-id", content)
