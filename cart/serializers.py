from rest_framework import serializers
from .models import Cart, CartItem
from products.models import NyscKit, NyscTour, Church
from products.serializers import NyscKitSerializer, NyscTourSerializer, ChurchSerializer
from django.contrib.contenttypes.models import ContentType

class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    product_id = serializers.UUIDField(write_only=True)
    product_type = serializers.CharField(write_only=True) # e.g., 'nysckit', 'nysctour', 'church'
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price', 'product_id', 'product_type']

    def get_product(self, obj):
        item = obj.content_object
        if isinstance(item, NyscKit):
            return NyscKitSerializer(item).data
        elif isinstance(item, NyscTour):
            return NyscTourSerializer(item).data
        elif isinstance(item, Church):
            return ChurchSerializer(item).data
        return str(item)

    def create(self, validated_data):
        product_id = validated_data.pop('product_id')
        product_type = validated_data.pop('product_type')
        cart = validated_data.get('cart')
        
        # Determine model based on type
        model_map = {
            'nysckit': NyscKit,
            'nysctour': NyscTour,
            'church': Church
        }
        
        model = model_map.get(product_type.lower())
        if not model:
            raise serializers.ValidationError("Invalid product type")
            
        content_type = ContentType.objects.get_for_model(model)
        
        # Check availability
        try:
            product = model.objects.get(id=product_id)
            if not product.can_be_purchased:
                 raise serializers.ValidationError("Product is not available")
        except model.DoesNotExist:
             raise serializers.ValidationError("Product not found")

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
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'created_at', 'updated_at']
