"""
DRF serializers for Cart and CartItem models.

Handles serialization/deserialization of cart data with polymorphic product support.
Validates product availability and manages cart item creation with automatic deduplication.
"""

from rest_framework import serializers
from .models import Cart, CartItem
from products.models import NyscKit, NyscTour, Church
from products.serializers import NyscKitSerializer, NyscTourSerializer, ChurchSerializer
from django.contrib.contenttypes.models import ContentType


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer for CartItem model.

    Handles polymorphic product relationships by accepting product_type and product_id
    on write operations, and returning full product data on read operations.

    Fields:
        - id: Cart item identifier
        - product (read-only): Full product data (polymorphic based on type)
        - quantity: Number of items
        - total_price (read-only): Calculated total (quantity * price)
        - product_id (write-only): UUID of the product to add
        - product_type (write-only): Type of product ('nysckit', 'nysctour', 'church')

    Validation:
        - Ensures product exists
        - Checks product availability (can_be_purchased)
        - Validates product_type against supported types

    Features:
        - Uses update_or_create to prevent duplicate cart items
        - Combines quantity on duplicate additions
        - Supports extra_fields for additional item metadata
    """

    product = serializers.SerializerMethodField()
    product_id = serializers.UUIDField(write_only=True)
    product_type = serializers.CharField(write_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product', 'quantity', 'total_price', 'product_id', 'product_type', 'extra_fields']
        extra_kwargs = {
            'cart': {'required': False},
            'extra_fields': {'required': False, 'write_only': False}
        }

    def validate_quantity(self, value):
        """Validate that quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def get_product(self, obj):
        """
        Serialize the product based on its type.

        Determines the product type via content_object and uses the appropriate
        serializer for that product type.

        Args:
            obj: CartItem instance

        Returns:
            dict: Serialized product data
            str: String representation if product type not recognized
        """
        item = obj.content_object
        if isinstance(item, NyscKit):
            return NyscKitSerializer(item).data
        elif isinstance(item, NyscTour):
            return NyscTourSerializer(item).data
        elif isinstance(item, Church):
            return ChurchSerializer(item).data
        return str(item)

    def create(self, validated_data):
        """
        Create or update a cart item.

        Extracts product information, validates availability, and creates/updates
        the cart item. Uses update_or_create to handle duplicate products by
        updating the quantity instead of creating duplicates.

        Args:
            validated_data: Validated serializer data

        Returns:
            CartItem: Created or updated cart item instance

        Raises:
            ValidationError: If product type is invalid, product doesn't exist,
                           or product is not available for purchase
        """
        product_id = validated_data.pop('product_id')
        product_type = validated_data.pop('product_type')
        cart = validated_data.get('cart')

        # Validate that cart is provided
        if not cart:
            raise serializers.ValidationError({"cart": "Cart ID is required."})

        # Map product type string to model class
        model_map = {
            'nysckit': NyscKit,
            'nysctour': NyscTour,
            'church': Church
        }

        model = model_map.get(product_type.lower())
        if not model:
            raise serializers.ValidationError("Invalid product type")

        content_type = ContentType.objects.get_for_model(model)

        # Validate product existence and availability
        try:
            product = model.objects.get(id=product_id)
            if not product.can_be_purchased:
                raise serializers.ValidationError("Product is not available")
        except model.DoesNotExist:
            raise serializers.ValidationError("Product not found")

        # Create or update cart item (prevents duplicates)
        cart_item, created = CartItem.objects.update_or_create(
            cart=cart,
            content_type=content_type,
            object_id=product_id,
            defaults={
                'quantity': validated_data.get('quantity', 1),
                'extra_fields': validated_data.get('extra_fields', {})
            }
        )
        return cart_item


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for Cart model.

    Provides complete cart representation including nested items and calculated totals.

    Fields:
        - id: Cart UUID
        - user: User ID (null for anonymous carts)
        - items (read-only): List of cart items with full product data
        - total_price (read-only): Sum of all item totals
        - created_at: Cart creation timestamp
        - updated_at: Last modification timestamp

    Features:
        - Nested serialization of cart items
        - Read-only items (managed via CartItem endpoints)
        - Automatic total price calculation
    """

    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'created_at', 'updated_at']
        extra_kwargs = {
            'id': {'read_only': True},
            'user': {'read_only': True}
        }

    def to_representation(self, instance):
        """Convert UUIDs to strings for JSON serialization."""
        data = super().to_representation(instance)
        if data.get('id'):
            data['id'] = str(data['id'])
        if data.get('user'):
            data['user'] = str(data['user'])
        return data
