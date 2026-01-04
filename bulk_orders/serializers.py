from rest_framework import serializers
from .models import BulkOrderLink, CouponCode, OrderEntry

class CouponCodeSerializer(serializers.ModelSerializer):
    bulk_order_name = serializers.CharField(source='bulk_order.organization_name', read_only=True)
    bulk_order_slug = serializers.CharField(source='bulk_order.slug', read_only=True)
    
    class Meta:
        model = CouponCode
        fields = ['id', 'bulk_order', 'bulk_order_name', 'bulk_order_slug', 'code', 'is_used', 'created_at']
        read_only_fields = ('id', 'is_used', 'created_at')

class BulkOrderLinkSummarySerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()
    shareable_url = serializers.SerializerMethodField()

    class Meta:
        model = BulkOrderLink
        fields = [
            'id',
            'slug',
            'organization_name',
            'price_per_item',
            'custom_branding_enabled',
            'payment_deadline',
            'is_expired',
            'shareable_url',
        ]

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_shareable_url(self, obj):
        request = self.context.get('request')
        path = obj.get_shareable_url()
        return request.build_absolute_uri(path) if request else path


class OrderEntrySerializer(serializers.ModelSerializer):
    bulk_order = BulkOrderLinkSummarySerializer(read_only=True)
    coupon_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    custom_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = OrderEntry
        fields = [
            'id', 'bulk_order', 'serial_number', 'email', 'full_name', 'size',
            'custom_name', 'coupon_used', 'paid', 'created_at', 'updated_at', 'coupon_code'
        ]
        read_only_fields = (
            'id', 'bulk_order', 'serial_number',
            'coupon_used', 'paid', 'created_at', 'updated_at'
        )


    def to_representation(self, instance):
        """Conditionally include custom_name based on bulk_order settings"""
        representation = super().to_representation(instance)
        
        # ✅ FIX: Only include custom_name if custom branding is enabled
        if not instance.bulk_order.custom_branding_enabled:
            representation.pop('custom_name', None)
        
        return representation

    def validate(self, attrs):
        # Get bulk_order from context (passed from ViewSet)
        bulk_order = self.context.get('bulk_order')
        
        if not bulk_order:
            raise serializers.ValidationError({"bulk_order": "Bulk order context is required."})
        
        attrs['bulk_order'] = bulk_order
        
        # ✅ FIX: Validate custom_name only if branding is enabled
        if not bulk_order.custom_branding_enabled:
            attrs.pop('custom_name', None)  # Remove custom_name if not enabled
        
        # ✅ FIX: Validate coupon belongs to THIS specific bulk_order
        coupon_code_str = attrs.pop('coupon_code', None)
        if coupon_code_str:
            try:
                coupon = CouponCode.objects.get(
                    code=coupon_code_str, 
                    bulk_order=bulk_order,  # ✅ Must match THIS bulk order
                    is_used=False
                )
                attrs['coupon_used'] = coupon
                # ✅ FIX: When coupon is used, automatically mark as paid
                attrs['paid'] = True
            except CouponCode.DoesNotExist:
                raise serializers.ValidationError({
                    "coupon_code": f"Invalid coupon code or coupon does not belong to {bulk_order.organization_name}. Please check your code."
                })
        
        return attrs

    def create(self, validated_data):
        coupon_used = validated_data.get('coupon_used')
        
        instance = super().create(validated_data)
        
        # Mark coupon as used
        if coupon_used:
            coupon_used.is_used = True
            coupon_used.save()
            
        return instance

class BulkOrderLinkSerializer(serializers.ModelSerializer):
    orders = OrderEntrySerializer(many=True, read_only=True)
    order_count = serializers.IntegerField(source='orders.count', read_only=True)
    paid_count = serializers.SerializerMethodField()
    coupon_count = serializers.IntegerField(source='coupons.count', read_only=True)
    shareable_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BulkOrderLink
        fields = [
            'id', 'slug', 'organization_name', 'price_per_item', 'custom_branding_enabled',
            'payment_deadline', 'created_by', 'created_at', 'updated_at', 
            'orders', 'order_count', 'paid_count', 'coupon_count', 'shareable_url'
        ]
        read_only_fields = ('created_by', 'created_at', 'updated_at', 'slug')
        lookup_field = 'slug'

    def get_paid_count(self, obj):
        return obj.orders.filter(paid=True).count()
    
    def get_shareable_url(self, obj):
        """Build absolute URL dynamically from request context"""
        request = self.context.get('request')
        if request and obj.slug:
            # Get the relative path from model
            path = obj.get_shareable_url()
            # Build absolute URI using request
            return request.build_absolute_uri(path)
        # Fallback to just the path if no request context
        return obj.get_shareable_url() if obj.slug else None

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)