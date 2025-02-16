from django.contrib import admin
from .models import Measurement


def get_list_display(model, exclude_fields=[]):
    """Get all fields for list display except excluded ones."""
    all_fields = [field.name for field in model._meta.fields]
    return [field for field in all_fields if field not in exclude_fields]


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = get_list_display(Measurement, exclude_fields=["id"])
    list_filter = ["created_at", "updated_at"]  # Add filtering
    search_fields = ["user__username"]  # Add search
    readonly_fields = ["created_at", "updated_at"]  # Protect timestamps

    def get_queryset(self, request):
        # Optimize queries by selecting related user
        return super().get_queryset(request).select_related("user")
