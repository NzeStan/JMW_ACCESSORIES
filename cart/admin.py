"""
Django admin configuration for Cart and CartItem models.

Provides administrative interfaces for managing shopping carts and cart items,
including inline editing of cart items within cart detail views.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    """
    Inline admin for CartItem model.

    Allows staff to view and edit cart items directly within the cart detail page.
    Displays product information, quantity, and total price for each item.
    """

    model = CartItem
    extra = 0
    fields = ('content_type', 'object_id', 'content_object_display', 'quantity', 'total_price', 'extra_fields')
    readonly_fields = ('content_object_display', 'total_price')

    def content_object_display(self, obj):
        """
        Display the content object in a readable format.

        Args:
            obj: CartItem instance

        Returns:
            String representation of the related product
        """
        if obj.content_object:
            return format_html('<strong>{}</strong>', str(obj.content_object))
        return '-'

    content_object_display.short_description = 'Product'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Admin interface for Cart model.

    Features:
    - List display with user, item count, total price, and timestamps
    - Filtering by creation date and user
    - Search by user email and cart ID
    - Inline editing of cart items
    - Readonly fields for calculated values
    """

    list_display = ('id', 'user_display', 'item_count', 'total_price_display', 'created_at', 'updated_at')
    list_filter = ('created_at', 'user')
    search_fields = ('id', 'user__email', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at', 'total_price_display')
    inlines = [CartItemInline]
    ordering = ('-created_at',)

    fieldsets = (
        ('Cart Information', {
            'fields': ('id', 'user', 'created_at', 'updated_at')
        }),
        ('Summary', {
            'fields': ('total_price_display',)
        }),
    )

    def user_display(self, obj):
        """
        Display user information or indicate anonymous cart.

        Args:
            obj: Cart instance

        Returns:
            Formatted user email or 'Anonymous'
        """
        if obj.user:
            return format_html('<strong>{}</strong>', obj.user.email)
        return format_html('<em>Anonymous</em>')

    user_display.short_description = 'User'
    user_display.admin_order_field = 'user'

    def item_count(self, obj):
        """
        Count the number of items in the cart.

        Args:
            obj: Cart instance

        Returns:
            Number of items in cart
        """
        return obj.items.count()

    item_count.short_description = 'Items'

    def total_price_display(self, obj):
        """
        Display formatted total price.

        Args:
            obj: Cart instance

        Returns:
            Formatted price string
        """
        return format_html('<strong>₦{}</strong>', obj.total_price)

    total_price_display.short_description = 'Total Price'
    total_price_display.admin_order_field = 'total_price'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Admin interface for CartItem model.

    Features:
    - List display with cart, product, quantity, and total price
    - Filtering by cart
    - Search by cart ID
    - Readonly fields for calculated values
    """

    list_display = ('id', 'cart', 'content_object_display', 'quantity', 'total_price_display')
    list_filter = ('cart',)
    search_fields = ('cart__id', 'cart__user__email')
    readonly_fields = ('total_price', 'content_object_display')

    fieldsets = (
        ('Cart Item Information', {
            'fields': ('cart', 'content_type', 'object_id', 'content_object_display')
        }),
        ('Quantity & Price', {
            'fields': ('quantity', 'total_price')
        }),
        ('Additional Information', {
            'fields': ('extra_fields',),
            'classes': ('collapse',)
        }),
    )

    def content_object_display(self, obj):
        """
        Display the content object in a readable format.

        Args:
            obj: CartItem instance

        Returns:
            String representation of the related product
        """
        if obj.content_object:
            return format_html('<strong>{}</strong><br/><small>Type: {}</small>',
                             str(obj.content_object),
                             obj.content_type.model)
        return '-'

    content_object_display.short_description = 'Product'

    def total_price_display(self, obj):
        """
        Display formatted total price.

        Args:
            obj: CartItem instance

        Returns:
            Formatted price string
        """
        return format_html('<strong>₦{}</strong>', obj.total_price)

    total_price_display.short_description = 'Total Price'
