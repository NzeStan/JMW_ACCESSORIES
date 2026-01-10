from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem
from cart.models import Cart
from products.models import NyscKit, NyscTour, Church
from products.serializers import NyscKitSerializer, NyscTourSerializer, ChurchSerializer
from jmw.background_utils import send_order_confirmation_email_async, generate_order_confirmation_pdf_task
import logging

logger = logging.getLogger(__name__)


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'price', 'quantity', 'extra_fields']

    def get_product(self, obj):
        item = obj.product
        if isinstance(item, NyscKit):
            return NyscKitSerializer(item).data
        elif isinstance(item, NyscTour):
            return NyscTourSerializer(item).data
        elif isinstance(item, Church):
            return ChurchSerializer(item).data
        return str(item)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    cart_id = serializers.UUIDField(write_only=True, required=False)  # Optional if we use user's cart

    class Meta:
        model = Order
        fields = [
            'id', 'reference', 'user', 'first_name', 'last_name', 'email', 'phone_number',
            'address', 'city', 'state',
            'created', 'updated', 'paid', 'total_cost', 'status', 'delivery_details',
            'items', 'cart_id'
        ]
        read_only_fields = ['reference', 'user', 'created', 'updated', 'paid', 'total_cost', 'status', 'items']

    @transaction.atomic
    def create(self, validated_data):
        cart_id = validated_data.pop('cart_id', None)
        user = validated_data.pop('user', None)  # ✅ Pop user from validated_data to avoid duplicate
        
        # Resolve Cart
        cart = None
        if cart_id:
            try:
                cart = Cart.objects.get(id=cart_id)
            except Cart.DoesNotExist:
                raise serializers.ValidationError("Invalid Cart ID")
        elif user:
            try:
                cart = Cart.objects.get(user=user)
            except Cart.DoesNotExist:
                raise serializers.ValidationError("User has no cart")

        if not cart or not cart.items.exists():
            raise serializers.ValidationError("Cart is empty")

        # Create Order (reference will be auto-generated)
        order = Order.objects.create(
            user=user,  # ✅ Now using the popped user value
            total_cost=cart.total_price,
            **validated_data
        )

        # Move items from cart to order
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                content_type=item.content_type,
                object_id=item.object_id,
                price=item.content_object.price,
                quantity=item.quantity,
                extra_fields=item.extra_fields
            )

        # Clear Cart (keep cart object, just clear items)
        cart.items.all().delete()

        # Send order confirmation email asynchronously (payment pending)
        try:
            send_order_confirmation_email_async(str(order.id))
            logger.info(f"Order confirmation email queued for order: {order.reference}")
        except Exception as e:
            logger.error(f"Failed to queue order confirmation email for {order.reference}: {str(e)}")

        # Queue PDF generation in background
        try:
            generate_order_confirmation_pdf_task(str(order.id))
            logger.info(f"Order confirmation PDF task queued for order: {order.reference}")
        except Exception as e:
            logger.error(f"Failed to queue order confirmation PDF for {order.reference}: {str(e)}")

        return order
