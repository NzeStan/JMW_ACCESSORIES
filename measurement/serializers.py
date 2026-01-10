from rest_framework import serializers
from .models import Measurement


class MeasurementSerializer(serializers.ModelSerializer):
    """Serializer for the Measurement model with custom validation and error messages."""

    class Meta:
        model = Measurement
        fields = "__all__"
        read_only_fields = ("user", "created_at", "updated_at", "is_deleted")
        extra_kwargs = {
            "chest": {
                "error_messages": {
                    "min_value": "Chest measurement must be at least 20 inches.",
                    "max_value": "Chest measurement cannot exceed 70 inches.",
                }
            },
            "shoulder": {
                "error_messages": {
                    "min_value": "Shoulder measurement must be at least 12 inches.",
                    "max_value": "Shoulder measurement cannot exceed 30 inches.",
                }
            },
            "neck": {
                "error_messages": {
                    "min_value": "Neck measurement must be at least 10 inches.",
                    "max_value": "Neck measurement cannot exceed 30 inches.",
                }
            },
            "sleeve_length": {
                "error_messages": {
                    "min_value": "Sleeve length must be at least 20 inches.",
                    "max_value": "Sleeve length cannot exceed 40 inches.",
                }
            },
            "sleeve_round": {
                "error_messages": {
                    "min_value": "Sleeve round (bicep) must be at least 8 inches.",
                    "max_value": "Sleeve round (bicep) cannot exceed 20 inches.",
                }
            },
            "top_length": {
                "error_messages": {
                    "min_value": "Top length must be at least 20 inches.",
                    "max_value": "Top length cannot exceed 40 inches.",
                }
            },
            "waist": {
                "error_messages": {
                    "min_value": "Waist measurement must be at least 20 inches.",
                    "max_value": "Waist measurement cannot exceed 60 inches.",
                }
            },
            "thigh": {
                "error_messages": {
                    "min_value": "Thigh measurement must be at least 12 inches.",
                    "max_value": "Thigh measurement cannot exceed 40 inches.",
                }
            },
            "knee": {
                "error_messages": {
                    "min_value": "Knee measurement must be at least 10 inches.",
                    "max_value": "Knee measurement cannot exceed 30 inches.",
                }
            },
            "ankle": {
                "error_messages": {
                    "min_value": "Ankle measurement must be at least 7 inches.",
                    "max_value": "Ankle measurement cannot exceed 20 inches.",
                }
            },
            "hips": {
                "error_messages": {
                    "min_value": "Hip measurement must be at least 25 inches.",
                    "max_value": "Hip measurement cannot exceed 70 inches.",
                }
            },
            "trouser_length": {
                "error_messages": {
                    "min_value": "Trouser length must be at least 25 inches.",
                    "max_value": "Trouser length cannot exceed 50 inches.",
                }
            },
        }

    def validate(self, data):
        """Ensure at least one measurement is provided."""
        measurement_fields = [
            "chest",
            "shoulder",
            "neck",
            "sleeve_length",
            "sleeve_round",
            "top_length",
            "waist",
            "thigh",
            "knee",
            "ankle",
            "hips",
            "trouser_length",
        ]

        # Check if this is an update (partial or full)
        if self.instance:
            # For updates, check combined existing and new data
            has_measurement = any(
                data.get(field) is not None or getattr(self.instance, field) is not None
                for field in measurement_fields
            )
        else:
            # For create, only check new data
            has_measurement = any(data.get(field) is not None for field in measurement_fields)

        if not has_measurement:
            raise serializers.ValidationError(
                "At least one measurement must be provided."
            )

        return data

    def create(self, validated_data):
        """Assign current user to measurement on create."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Ensure user cannot be changed on update."""
        validated_data["user"] = instance.user
        return super().update(instance, validated_data)
