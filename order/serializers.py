from rest_framework import serializers
from .models import Order, OrderItem
from cart.models import Cart
from products.models import NyscKit, NyscTour, Church
from products.serializers import NyscKitSerializer, NyscTourSerializer, ChurchSerializer

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
    cart_id = serializers.UUIDField(write_only=True, required=False) # Optional if we use user's cart

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'first_name', 'last_name', 'email', 'phone_number',
            'created', 'updated', 'paid', 'total_cost', 'status', 'delivery_details',
            'items', 'cart_id'
        ]
        read_only_fields = ['user', 'created', 'updated', 'paid', 'total_cost', 'status', 'items']

    def create(self, validated_data):
        cart_id = validated_data.pop('cart_id', None)
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        
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

        # Create Order
        order = Order.objects.create(
            user=user,
            total_cost=cart.total_price,
            **validated_data
        )

        # Move items
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                content_type=item.content_type,
                object_id=item.object_id,
                price=item.content_object.price,
                quantity=item.quantity,
                extra_fields=item.extra_fields
            )
            
        # Clear Cart
        cart.items.all().delete()
        # cart.delete() # Optional: keep cart for history or just clear items
        
        return order
