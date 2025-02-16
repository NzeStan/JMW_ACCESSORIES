from django.contrib import admin
from django.utils.html import format_html
from .models import EmailEvent, Bounce, Complaint


@admin.register(EmailEvent)
class EmailEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message_id",
        "event_type",
        "recipient",
        "timestamp",
        "raw_data",
    )


@admin.register(Bounce)
class BounceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email_event",
        "bounce_type",
        "bounce_subtype",
    )


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email_event",
        "complaint_type",
        "feedback_id",
    )
