from rest_framework import serializers
from .models import Image

class ImageSerializer(serializers.ModelSerializer):
    optimized_url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'url', 'upload_date', 'active', 'optimized_url']
        read_only_fields = ('id', 'upload_date')

    def get_optimized_url(self, obj):
        return obj.get_optimized_url()
