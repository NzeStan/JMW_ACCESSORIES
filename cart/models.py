"""
Django models for shopping cart functionality.

Provides Cart and CartItem models for managing user shopping carts
with support for both authenticated and anonymous users.
Uses Django's ContentType framework for polymorphic product relationships.
"""

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

import uuid


class Cart(models.Model):
    """
    Shopping cart model.

    Represents a shopping cart that can be associated with a user or remain anonymous.
    Each user can have only one cart (OneToOne relationship), while anonymous carts
    are identified by their UUID.

    Attributes:
        id (UUIDField): Primary key using UUID4 for security
        user (OneToOneField): Optional link to authenticated user
        created_at (DateTimeField): Timestamp of cart creation
        updated_at (DateTimeField): Timestamp of last cart update

    Properties:
        total_price: Calculated total price of all items in cart

    Related:
        items (CartItem): Related cart items via 'cart' foreign key
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """
        String representation of the cart.

        Returns:
            str: Cart ID with user email or 'Anonymous'
        """
        return f"Cart {self.id} ({self.user.email if self.user else 'Anonymous'})"

    @property
    def total_price(self):
        """
        Calculate the total price of all items in the cart.

        Iterates through all cart items and sums their total prices.
        Returns 0 for empty carts.

        Returns:
            Decimal: Total price of all cart items
        """
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    """
    Cart item model representing a product added to a cart.

    Uses Django's GenericForeignKey to support multiple product types
    (NyscKit, NyscTour, Church) without explicit foreign keys.

    Attributes:
        cart (ForeignKey): Parent cart
        content_type (ForeignKey): ContentType of the product model
        object_id (UUIDField): UUID of the product instance
        content_object (GenericForeignKey): The actual product object
        quantity (PositiveIntegerField): Number of items (default=1)
        extra_fields (JSONField): Flexible storage for additional data

    Properties:
        total_price: Calculated price (quantity * product price)

    Constraints:
        unique_together: (cart, content_type, object_id) - prevents duplicate products
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')

    # Generic relation to support multiple product types
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')

    quantity = models.PositiveIntegerField(default=1)
    extra_fields = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('cart', 'content_type', 'object_id')

    def __str__(self):
        """
        String representation of the cart item.

        Returns:
            str: Quantity and product name
        """
        return f"{self.quantity} x {self.content_object}"

    @property
    def total_price(self):
        """
        Calculate the total price for this cart item.

        Multiplies the product's unit price by the quantity.

        Returns:
            Decimal: Total price (product.price * quantity)
        """
        return self.content_object.price * self.quantity
