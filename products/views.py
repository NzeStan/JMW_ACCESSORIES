from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, NyscKit, NyscTour, Church
from .serializers import (
    CategorySerializer, 
    NyscKitSerializer, 
    NyscTourSerializer, 
    ChurchSerializer
)

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    lookup_field = 'slug'

class BaseProductViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created']
    filterset_fields = ['available', 'out_of_stock', 'category__slug']

    def get_queryset(self):
        return super().get_queryset().select_related('category').filter(available=True)

class NyscKitViewSet(BaseProductViewSet):
    queryset = NyscKit.objects.all()
    serializer_class = NyscKitSerializer
    lookup_field = 'slug'
    filterset_fields = BaseProductViewSet.filterset_fields + ['type']

class NyscTourViewSet(BaseProductViewSet):
    queryset = NyscTour.objects.all()
    serializer_class = NyscTourSerializer
    lookup_field = 'slug'

class ChurchViewSet(BaseProductViewSet):
    queryset = Church.objects.all()
    serializer_class = ChurchSerializer
    lookup_field = 'slug'
    filterset_fields = BaseProductViewSet.filterset_fields + ['church']
