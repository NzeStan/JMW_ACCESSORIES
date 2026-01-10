from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    # ✅ Changed to IsAuthenticatedOrReadOnly for list, but allow POST without auth for guest checkout
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # ✅ Only return orders for authenticated users
        if not self.request.user.is_authenticated:
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'items__product')

    def get_permissions(self):
        """
        Override permissions:
        - create: Allow anyone (for guest checkout)
        - list, retrieve, update, delete: Require authentication
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        # If user is authenticated, associate order with user
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            # Guest checkout - no user association
            serializer.save()