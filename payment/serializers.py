from rest_framework import serializers
from .models import PaymentTransaction

class PaymentInitializeSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    email = serializers.EmailField()

class PaymentVerifySerializer(serializers.Serializer):
    reference = serializers.CharField()

class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = '__all__'
