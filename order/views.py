from rest_framework import viewsets, permissions
from .models import Order
from .serializers import OrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny] # Allow creation by anonymous users

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'items__product')

    def perform_create(self, serializer):
        # If user is anonymous, they can still create order, but we need to handle it.
        # But here permission is IsAuthenticated. 
        # For guest checkout, we'd need to relax permission and rely on return data.
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()
