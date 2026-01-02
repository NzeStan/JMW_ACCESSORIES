from rest_framework import serializers
from .models import BulkOrderLink, CouponCode, OrderEntry

class CouponCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponCode
        fields = '__all__'
        read_only_fields = ('is_used', 'created_at')

class OrderEntrySerializer(serializers.ModelSerializer):
    coupon_code = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = OrderEntry
        fields = [
            'id', 'bulk_order', 'serial_number', 'email', 'full_name', 'size',
            'custom_name', 'coupon_used', 'paid', 'created_at', 'updated_at', 'coupon_code'
        ]
        read_only_fields = ('serial_number', 'coupon_used', 'paid', 'created_at', 'updated_at')

    def validate(self, attrs):
        coupon_code_str = attrs.get('coupon_code')
        if coupon_code_str:
            try:
                coupon = CouponCode.objects.get(code=coupon_code_str, bulk_order=attrs['bulk_order'], is_used=False)
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
    
    class Meta:
        model = BulkOrderLink
        fields = [
            'id', 'organization_name', 'price_per_item', 'custom_branding_enabled',
            'payment_deadline', 'created_by', 'created_at', 'updated_at', 'orders'
        ]
        read_only_fields = ('created_by', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
