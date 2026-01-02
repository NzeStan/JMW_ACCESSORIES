from rest_framework import viewsets, permissions, views, response, status
from .models import Image
from .serializers import ImageSerializer
from .youtube_service import YouTubeService

class ImageViewSet(viewsets.ModelViewSet):
    serializer_class = ImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Image.objects.filter(active=True)

    def get_queryset(self):
        if self.request.user.is_staff:
            return Image.objects.all()
        return Image.objects.filter(active=True)

class YouTubeVideoView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            service = YouTubeService()
            videos = service.get_channel_videos()
            return response.Response(videos)
        except Exception as e:
            return response.Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
