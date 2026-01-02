from rest_framework import serializers
from .models import Category, NyscKit, NyscTour, Church

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'product_type', 'description']

class BaseProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    
    class Meta:
        fields = [
            'id', 'category', 'image', 'image_1', 'image_2', 'image_3',
            'description', 'price', 'available', 'out_of_stock', 
            'created', 'updated', 'display_status'
        ]

class NyscKitSerializer(BaseProductSerializer):
    class Meta(BaseProductSerializer.Meta):
        model = NyscKit
        fields = BaseProductSerializer.Meta.fields + ['name', 'slug', 'type']

class NyscTourSerializer(BaseProductSerializer):
    class Meta(BaseProductSerializer.Meta):
        model = NyscTour
        fields = BaseProductSerializer.Meta.fields + ['name', 'slug']

class ChurchSerializer(BaseProductSerializer):
    class Meta(BaseProductSerializer.Meta):
        model = Church
        fields = BaseProductSerializer.Meta.fields + ['name', 'slug', 'church']
