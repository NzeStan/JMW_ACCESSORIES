from rest_framework import viewsets, permissions
from .models import Measurement
from .serializers import MeasurementSerializer

class MeasurementViewSet(viewsets.ModelViewSet):
    serializer_class = MeasurementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Measurement.objects.filter(user=self.request.user)
