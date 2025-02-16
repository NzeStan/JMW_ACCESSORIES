# comments/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Comment

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class RecursiveSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    replies = RecursiveSerializer(many=True, read_only=True)
    reply_count = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "content",
            "created_at",
            "created_at_formatted",
            "updated_at",
            "replies",
            "reply_count",
            "parent",
            "is_admin",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]

    def get_reply_count(self, obj):
        return obj.replies.count()

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%B %d, %Y %I:%M %p")

    def get_is_admin(self, obj):
        return obj.is_admin


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["content", "parent"]
