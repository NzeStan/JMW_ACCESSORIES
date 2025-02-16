from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from .models import Comment
from .serializers import CommentSerializer, CommentCreateSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    # Define allowed content types for each app
    ALLOWED_CONTENT_TYPES = {
        "blog": ["post"],
        "products": ["nysctour", "church", "nysckit"],
    }

    def get_serializer_class(self):
        if self.action == "create":
            return CommentCreateSerializer
        return CommentSerializer

    def get_queryset(self):
        # Remove the parent=None filter to get all comments
        queryset = Comment.objects.all()
        content_type = self.request.query_params.get("content_type", "")
        object_id = self.request.query_params.get("object_id", "")

        if content_type and object_id:
            try:
                content_type_lower = content_type.lower()
                app_label = None

                for app, allowed_types in self.ALLOWED_CONTENT_TYPES.items():
                    if content_type_lower in allowed_types:
                        app_label = app
                        break

                if not app_label:
                    return Comment.objects.none()

                model = apps.get_model(app_label, content_type)
                content_type_obj = ContentType.objects.get_for_model(model)
                queryset = queryset.filter(
                    content_type=content_type_obj, object_id=object_id
                ).filter(
                    parent=None
                )  # Only get top-level comments here

            except (ContentType.DoesNotExist, LookupError):
                return Comment.objects.none()

        return queryset.select_related("user").prefetch_related(
            "replies",
            "replies__user",  # Prefetch user data for replies
            "replies__replies",  # Prefetch nested replies
        )

    def perform_create(self, serializer):
        content_type = self.request.data.get("content_type")
        object_id = self.request.data.get("object_id")
        parent_id = self.request.data.get("parent")

        if not content_type or not object_id:
            raise ValidationError("content_type and object_id are required")

        try:
            # Determine app label based on content type
            content_type_lower = content_type.lower()
            app_label = None

            for app, allowed_types in self.ALLOWED_CONTENT_TYPES.items():
                if content_type_lower in allowed_types:
                    app_label = app
                    break

            if not app_label:
                raise ValidationError("Invalid content type")

            # Get the model class and content type
            model = apps.get_model(app_label, content_type)
            content_type_obj = ContentType.objects.get_for_model(model)

            # Verify the object exists
            try:
                model.objects.get(id=object_id)
            except model.DoesNotExist:
                raise ValidationError(f"Object with id {object_id} does not exist")

            # Get parent comment if it exists
            parent = None
            if parent_id:
                try:
                    parent = Comment.objects.get(id=parent_id)
                except Comment.DoesNotExist:
                    raise ValidationError(
                        f"Parent comment with id {parent_id} does not exist"
                    )

            serializer.save(
                user=self.request.user,
                content_type=content_type_obj,
                object_id=object_id,
                parent=parent,
            )

        except (ContentType.DoesNotExist, LookupError) as e:
            raise ValidationError(f"Invalid content type: {str(e)}")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.replies.exists():
            instance.content = "[deleted]"
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)
