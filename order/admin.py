from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Inline display of order items within an order"""
    model = OrderItem
    extra = 0
    readonly_fields = ["content_type", "object_id", "price", "quantity"]
    fields = ["content_type", "object_id", "price", "quantity", "extra_fields"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin interface for unified Order model"""
    list_display = [
        "id",
        "user",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "status",
        "paid",
        "total_cost",
        "created",
    ]
    list_filter = ["status", "paid", "created"]
    search_fields = [
        "id",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "user__email",
    ]
    readonly_fields = ["id", "created", "updated", "total_cost"]
    inlines = [OrderItemInline]
    
    fieldsets = (
        ("Order Information", {
            "fields": ("id", "user", "status", "paid", "total_cost")
        }),
        ("Customer Details", {
            "fields": ("first_name", "last_name", "email", "phone_number")
        }),
        ("Delivery Details", {
            "fields": ("delivery_details",),
            "description": "JSON field containing delivery-specific information"
        }),
        ("Timestamps", {
            "fields": ("created", "updated"),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        return super().get_queryset(request).select_related("user").prefetch_related("items")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin interface for order items"""
    list_display = [
        "id",
        "order",
        "content_type",
        "object_id",
        "price",
        "quantity",
        "get_total",
    ]
    list_filter = ["content_type"]
    search_fields = ["order__id", "order__email"]
    readonly_fields = ["get_total"]
    
    def get_total(self, obj):
        """Calculate total cost for this item"""
        return obj.get_cost()
    get_total.short_description = "Total Cost"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related("order", "content_type")