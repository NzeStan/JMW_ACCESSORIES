from rest_framework import serializers
from .models import BulkOrderLink, CouponCode, OrderEntry

class CouponCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponCode
        fields = '__all__'
        read_only_fields = ('is_used', 'created_at')

class OrderEntrySerializer(serializers.ModelSerializer):
    coupon_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    bulk_order_slug = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = OrderEntry
        fields = [
            'id', 'bulk_order', 'bulk_order_slug', 'serial_number', 'email', 'full_name', 'size',
            'custom_name', 'coupon_used', 'paid', 'created_at', 'updated_at', 'coupon_code'
        ]
        read_only_fields = ('serial_number', 'coupon_used', 'paid', 'created_at', 'updated_at', 'bulk_order')

    def validate(self, attrs):
        # Handle bulk_order lookup by slug or ID
        bulk_order_slug = attrs.pop('bulk_order_slug', None)
        if bulk_order_slug:
            try:
                bulk_order = BulkOrderLink.objects.get(slug=bulk_order_slug)
                attrs['bulk_order'] = bulk_order
            except BulkOrderLink.DoesNotExist:
                raise serializers.ValidationError({"bulk_order_slug": "Invalid bulk order link."})
        
        # Validate bulk_order is set
        if 'bulk_order' not in attrs:
            raise serializers.ValidationError({"bulk_order": "Bulk order is required."})
        
        # Validate coupon if provided
        coupon_code_str = attrs.get('coupon_code')
        if coupon_code_str:
            try:
                coupon = CouponCode.objects.get(
                    code=coupon_code_str, 
                    bulk_order=attrs['bulk_order'], 
                    is_used=False
                )
                attrs['coupon_used'] = coupon
            except CouponCode.DoesNotExist:
                raise serializers.ValidationError({"coupon_code": "Invalid or used coupon code."})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('coupon_code', None)
        coupon_used = validated_data.get('coupon_used')
        
        instance = super().create(validated_data)
        
        if coupon_used:
            coupon_used.is_used = True
            coupon_used.save()
            # If coupon covers full payment (logic depends on requirements), mark paid?
            # Assuming coupon logic handled elsewhere or manual verification for now.
            
        return instance

class BulkOrderLinkSerializer(serializers.ModelSerializer):
    orders = OrderEntrySerializer(many=True, read_only=True)
    order_count = serializers.IntegerField(source='orders.count', read_only=True)
    paid_count = serializers.SerializerMethodField()
    coupon_count = serializers.IntegerField(source='coupons.count', read_only=True)
    shareable_url = serializers.SerializerMethodField()  # ✅ Changed to SerializerMethodField
    
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