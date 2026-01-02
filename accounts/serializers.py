from rest_framework import serializers
from dj_rest_auth.serializers import UserDetailsSerializer
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserSerializer(UserDetailsSerializer):
    class Meta(UserDetailsSerializer.Meta):
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class CustomRegisterSerializer(RegisterSerializer):
    # Add custom fields here if needed in the future
    pass
