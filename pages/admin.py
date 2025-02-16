# pages/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Testimonial, VideoMessage


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "rating_stars",
        "short_comment",
        "created_at",
        "is_active",
        "user_email",
    )
    list_filter = ("rating", "is_active", "created_at")
    search_fields = ("name", "user__email", "comment")
    list_editable = ("is_active",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 20

    def rating_stars(self, obj):
        return "★" * obj.rating

    rating_stars.short_description = "Rating"

    def short_comment(self, obj):
        return obj.comment[:100] + "..." if len(obj.comment) > 100 else obj.comment

    short_comment.short_description = "Comment"

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "Email"

    actions = ["activate_testimonials", "deactivate_testimonials"]

    def activate_testimonials(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} testimonials have been activated.")

    activate_testimonials.short_description = "Activate selected testimonials"

    def deactivate_testimonials(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} testimonials have been deactivated.")

    deactivate_testimonials.short_description = "Deactivate selected testimonials"

    fieldsets = (
        ("User Information", {"fields": ("user", "name")}),
        ("Testimonial Content", {"fields": ("rating", "comment")}),
        ("Status", {"fields": ("is_active", "created_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(VideoMessage)
class VideoMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "video",
        "active",
    )
