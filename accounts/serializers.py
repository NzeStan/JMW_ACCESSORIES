from rest_framework import serializers
from dj_rest_auth.serializers import (
    UserDetailsSerializer, 
    LoginSerializer, 
    PasswordResetSerializer,
    PasswordResetConfirmSerializer
)
from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomUserSerializer(UserDetailsSerializer):
    email = serializers.EmailField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)
    
    class Meta(UserDetailsSerializer.Meta):
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_active', 
                 'date_joined', 'last_login')
        read_only_fields = ('id', 'email', 'is_active', 'date_joined', 'last_login')


class CustomRegisterSerializer(RegisterSerializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    
    def validate_password1(self, password):
        try:
            validate_password(password, self.instance)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return password
    
    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.update({
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
        })
        return data
    
    def save(self, request):
        user = super().save(request)
        logger.info(f"New user registered: {user.email}")
        return user


class CustomLoginSerializer(LoginSerializer):
    email = serializers.EmailField(required=True)
    username = None
    
    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Add custom validation if needed
        return attrs


class CustomPasswordResetSerializer(PasswordResetSerializer):
    def save(self):
        request = self.context.get('request')
        opts = {
            'use_https': request.is_secure(),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL'),
            'request': request,
            'html_email_template_name': 'registration/password_reset_email.html',
        }
        self.reset_form.save(**opts)
        logger.info(f"Password reset email sent for: {self.validated_data['email']}")


class CustomPasswordResetConfirmSerializer(PasswordResetConfirmSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Add password strength validation
        password = attrs['new_password1']
        try:
            validate_password(password, self.user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'new_password1': list(e.messages)})
        return attrs
    
    def save(self):
        self.user.set_password(self.validated_data['new_password1'])
        self.user.save()
        logger.info(f"Password reset successful for user: {self.user.email}")
        return self.user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password1 = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate(self, data):
        if data['new_password1'] != data['new_password2']:
            raise serializers.ValidationError({"new_password2": "Passwords don't match"})
        
        try:
            validate_password(data['new_password1'], self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password1": list(e.messages)})
        
        return data
    
    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password1'])
        user.save()
        logger.info(f"Password changed for user: {user.email}")
        return user