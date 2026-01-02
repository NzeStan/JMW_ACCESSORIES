from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer

class CartViewSet(viewsets.GenericViewSet, viewsets.mixins.RetrieveModelMixin, viewsets.mixins.CreateModelMixin, viewsets.mixins.DestroyModelMixin):
    serializer_class = CartSerializer
    queryset = Cart.objects.all()
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Cart.objects.filter(user=user)
        return Cart.objects.all() # For anonymous, they access by ID directly

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    queryset = CartItem.objects.all()

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return CartItem.objects.filter(cart__user=user).select_related('content_type').prefetch_related('content_object')
        # For anonymous users, we don't allow listing all items. 
        # They should access items via the Cart detail view or specific item ID if they know it.
        # But to support update/delete, we need to allow access if they have the ID.
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return CartItem.objects.all()
        return CartItem.objects.none()

    def create(self, request, *args, **kwargs):
        # Allow passing cart_id explicitly if anonymous
        cart_id = request.data.get('cart')
        if not cart_id and request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            request.data['cart'] = cart.id
            
        return super().create(request, *args, **kwargs)
