"""
DRF viewsets for Cart and CartItem models.

Provides RESTful API endpoints for managing shopping carts and cart items.
Supports both authenticated users and anonymous users with proper access control.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to modify it.

    Anonymous users can access objects they know the ID of, but only
    authenticated users can list their own objects.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access the specific object.

        Args:
            request: HTTP request
            view: ViewSet instance
            obj: Object being accessed (Cart or CartItem)

        Returns:
            Boolean indicating whether access is allowed
        """
        if request.method in permissions.SAFE_METHODS:
            if isinstance(obj, Cart):
                return not obj.user or obj.user == request.user
            elif isinstance(obj, CartItem):
                return not obj.cart.user or obj.cart.user == request.user

        if isinstance(obj, Cart):
            return not obj.user or obj.user == request.user
        elif isinstance(obj, CartItem):
            return not obj.cart.user or obj.cart.user == request.user

        return False


class CartViewSet(viewsets.GenericViewSet,
                   viewsets.mixins.RetrieveModelMixin,
                   viewsets.mixins.CreateModelMixin,
                   viewsets.mixins.DestroyModelMixin):
    """
    ViewSet for managing shopping carts.

    Provides endpoints for:
    - Creating carts (authenticated and anonymous users)
    - Retrieving cart details by ID
    - Deleting carts
    - Getting authenticated user's cart (/mine action)

    Permissions:
    - Anyone can create a cart
    - Only cart owners can retrieve/delete their carts
    - Anonymous carts can be accessed if ID is known
    """

    serializer_class = CartSerializer
    queryset = Cart.objects.all()
    permission_classes = [IsOwnerOrReadOnly]

    def create(self, request, *args, **kwargs):
        """Create a cart and associate with authenticated user if applicable."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set user for authenticated requests
        if request.user.is_authenticated:
            serializer.save(user=request.user)
        else:
            serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        """
        Filter queryset based on user authentication status.

        Authenticated users only see their own carts.
        Anonymous users can access any cart by ID directly.

        Returns:
            Filtered QuerySet
        """
        user = self.request.user
        if user.is_authenticated:
            return Cart.objects.filter(user=user)
        return Cart.objects.all()

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        """
        Get or create the authenticated user's cart.

        This endpoint automatically creates a cart for the user if one
        doesn't exist, ensuring users always have a cart available.

        Returns:
            Response: Serialized cart data
        """
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)


class CartItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing cart items.

    Provides full CRUD operations for cart items with proper user isolation.

    Permissions:
    - Authenticated users can list only their cart items
    - Anonymous users cannot list but can access specific items by ID
    - Users can only modify items in their own carts

    Features:
    - Automatic cart creation for authenticated users on item creation
    - Query optimization with select_related and prefetch_related
    - Support for explicit cart ID (for anonymous users)
    """

    serializer_class = CartItemSerializer
    queryset = CartItem.objects.all()
    permission_classes = [IsOwnerOrReadOnly]
    pagination_class = None  # Disable pagination for cart items

    def get_queryset(self):
        """
        Filter queryset based on user authentication and action.

        Authenticated users:
        - All actions: Only their cart items

        Anonymous users:
        - List action: Empty queryset
        - Other actions: All items (for retrieve/update/delete by ID)

        Returns:
            Filtered and optimized QuerySet
        """
        user = self.request.user
        queryset = CartItem.objects.all()

        if user.is_authenticated:
            # Authenticated users only see their own cart items
            queryset = queryset.filter(cart__user=user)
        elif self.action == 'list':
            # Anonymous users cannot list items
            queryset = queryset.none()

        return queryset.select_related('content_type').prefetch_related('content_object')

    def create(self, request, *args, **kwargs):
        """
        Create a new cart item.

        For authenticated users without a cart ID, automatically creates
        or retrieves their cart. For anonymous users, cart ID must be
        provided in the request data.

        Args:
            request: HTTP request with cart item data

        Returns:
            Response: Created cart item data or validation errors
        """
        # Create mutable copy of request data
        data = request.data.copy()
        cart_id = data.get('cart')

        if not cart_id and request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            data['cart'] = str(cart.id)

        # Pass modified data to serializer
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
