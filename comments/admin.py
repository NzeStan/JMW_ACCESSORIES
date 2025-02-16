# comments/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "content_type",
        "object_id",
        "short_content",
        "created_at",
        "has_replies",
    ]
    list_filter = ["content_type", "created_at"]
    search_fields = ["content", "user__username"]
    date_hierarchy = "created_at"
    raw_id_fields = ["user", "parent"]
    readonly_fields = ["created_at", "updated_at"]

    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    short_content.short_description = _("Content")

    def has_replies(self, obj):
        return obj.replies.exists()

    has_replies.boolean = True
    has_replies.short_description = _("Has replies")

    fieldsets = (
        (None, {"fields": ("user", "content", "parent")}),
        (_("Content Type Information"), {"fields": ("content_type", "object_id")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
