from rest_framework import viewsets, permissions, filters
from .models import BulkOrderLink, OrderEntry, CouponCode
from .serializers import BulkOrderLinkSerializer, OrderEntrySerializer, CouponCodeSerializer

class BulkOrderLinkViewSet(viewsets.ModelViewSet):
    serializer_class = BulkOrderLinkSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = BulkOrderLink.objects.all()

    def get_queryset(self):
        if self.request.user.is_staff:
             return BulkOrderLink.objects.all()
        # For public view, maybe filter by active? or just return all?
        # Assuming creators can see their own, and public can view via ID (DetailView).
        # For list, maybe only own?
        if self.request.user.is_authenticated:
            return BulkOrderLink.objects.filter(created_by=self.request.user)
        return BulkOrderLink.objects.none() # Or public links logic

class OrderEntryViewSet(viewsets.ModelViewSet):
    serializer_class = OrderEntrySerializer
    permission_classes = [permissions.AllowAny] # Allow public to submit orders?
    
    def get_queryset(self):
        # Users might want to see their own orders if authenticated
        if self.request.user.is_authenticated:
            return OrderEntry.objects.filter(email=self.request.user.email)
        return OrderEntry.objects.none()

    def perform_create(self, serializer):
        # Public creation logic is handled in serializer
        serializer.save()

class CouponCodeViewSet(viewsets.ModelViewSet):
    serializer_class = CouponCodeSerializer
    permission_classes = [permissions.IsAdminUser] # Only admin/staff manage coupons?
    queryset = CouponCode.objects.all()
