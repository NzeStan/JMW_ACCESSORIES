from rest_framework import viewsets, permissions
from rest_framework.throttling import UserRateThrottle
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Measurement
from .serializers import MeasurementSerializer


class MeasurementRateThrottle(UserRateThrottle):
    """Custom rate throttle for measurement API endpoints."""

    rate = "100/hour"


class MeasurementPagination(PageNumberPagination):
    """Custom pagination for measurement list views."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(description="List all measurements for the authenticated user"),
    create=extend_schema(description="Create a new measurement set"),
    retrieve=extend_schema(description="Retrieve a specific measurement set"),
    update=extend_schema(description="Update a measurement set"),
    partial_update=extend_schema(description="Partially update a measurement set"),
    destroy=extend_schema(description="Delete a measurement set (soft delete)"),
)
class MeasurementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing body measurements.

    All measurements are in inches with 2 decimal precision.
    Users can only access their own measurements.

    Features:
    - User-scoped access (authentication required)
    - Rate limiting (100 requests/hour per user)
    - Pagination (20 items per page by default)
    - Filtering by created_at and updated_at
    - Ordering by created_at and updated_at
    - Soft delete (measurements are marked as deleted, not removed)
    """

    serializer_class = MeasurementSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [MeasurementRateThrottle]
    pagination_class = MeasurementPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["created_at", "updated_at"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return only the authenticated user's measurements with optimized query."""
        return Measurement.objects.filter(user=self.request.user).select_related(
            "user"
        )
