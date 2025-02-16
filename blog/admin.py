from django.contrib import admin
from .models import Post
from django.utils import timezone

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # List view configuration
    list_display = ("title", "status", "created_date", "published_date", "view_count")
    # These fields will be shown as columns in the list view

    list_filter = ("status", "created_date", "published_date")
    # Adds filters in the right sidebar for quick filtering

    search_fields = ("title", "content")
    # Enables searching through titles and content

    prepopulated_fields = {"slug": ("title",)}
    # Automatically generates the slug from the title as you type

    date_hierarchy = "published_date"
    # Adds date-based navigation at the top

    readonly_fields = ("published_date",)

    ordering = ("-created_date",)
    # Default ordering in the admin list view

    # Detail view configuration
    fieldsets = (
        ("Post Content", {"fields": ("title", "slug", "content", "image")}),
        (
            "Publication Settings",
            {
                "fields": ("status", "published_date"),
                "description": "The published date will be set automatically when the post is published.",
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        # Additional logging for when posts are published
        if change and obj.status == "published" and obj.published_date is None:
            obj.published_date = timezone.now()
        super().save_model(request, obj, form, change)
