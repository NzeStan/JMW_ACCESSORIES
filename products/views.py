from rest_framework import viewsets, filters, permissions
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, NyscKit, NyscTour, Church
from .serializers import (
    CategorySerializer,
    NyscKitSerializer,
    NyscTourSerializer,
    ChurchSerializer
)


class ProductsPagination(PageNumberPagination):
    """Pagination for product listings"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductsRateThrottle(AnonRateThrottle):
    """Rate limit for anonymous users browsing products"""
    rate = '100/hour'


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only API for product categories.
    No authentication required.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ProductsRateThrottle, UserRateThrottle]
    pagination_class = ProductsPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']
    lookup_field = 'slug'

    def get_queryset(self):
        """Prefetch related products for efficient queries"""
        return Category.objects.prefetch_related('nysckit_set', 'nysctour_set', 'church_set')


class BaseProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Base viewset for all product types.
    Public read-only access - catalog is available to everyone.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ProductsRateThrottle, UserRateThrottle]
    pagination_class = ProductsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created', 'name']
    ordering = ['-created']
    filterset_fields = ['available', 'out_of_stock', 'category__slug']

    def get_queryset(self):
        """Filter to only show available products and optimize queries"""
        return super().get_queryset().select_related('category').filter(available=True)


class NyscKitViewSet(BaseProductViewSet):
    """
    API endpoint for NYSC Kit products.
    Public catalog - anyone can browse.
    """
    queryset = NyscKit.objects.all()
    serializer_class = NyscKitSerializer
    lookup_field = 'slug'
    filterset_fields = BaseProductViewSet.filterset_fields + ['type']


class NyscTourViewSet(BaseProductViewSet):
    """
    API endpoint for NYSC Tour products.
    Public catalog - anyone can browse.
    """
    queryset = NyscTour.objects.all()
    serializer_class = NyscTourSerializer
    lookup_field = 'slug'


class ChurchViewSet(BaseProductViewSet):
    """
    API endpoint for Church products.
    Public catalog - anyone can browse.
    """
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    lookup_field = 'slug'
    filterset_fields = BaseProductViewSet.filterset_fields + ['church']
