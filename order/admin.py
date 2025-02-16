# admin.py
from django.contrib import admin
from .models import BaseOrder, NyscKitOrder, NyscTourOrder, ChurchOrder, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ["content_type"]  # Remove object_id since it's a UUID
    extra = 0
    readonly_fields = ["object_id"]  # Make object_id readonly instead


@admin.register(BaseOrder)
class BaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        "serial_number",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "paid",
        "created",
    ]
    list_filter = ["paid", "created"]
    search_fields = ["first_name", "last_name", "email", "serial_number"]
    inlines = [OrderItemInline]


@admin.register(NyscKitOrder)
class NyscKitOrderAdmin(admin.ModelAdmin):
    list_display = [
        "serial_number",
        "first_name",
        "last_name",
        "state_code",
        "state",
        "local_government",
        "paid",
    ]
    list_filter = ["paid", "state"]
    search_fields = ["first_name", "last_name", "state_code", "serial_number"]
    inlines = [OrderItemInline]


@admin.register(NyscTourOrder)
class NyscTourOrderAdmin(admin.ModelAdmin):
    list_display = ["serial_number", "first_name", "last_name", "paid"]
    list_filter = ["paid"]
    search_fields = ["first_name", "last_name", "serial_number"]
    inlines = [OrderItemInline]


@admin.register(ChurchOrder)
class ChurchOrderAdmin(admin.ModelAdmin):
    list_display = [
        "serial_number",
        "first_name",
        "last_name",
        "pickup_on_camp",
        "delivery_state",
        "delivery_lga",
        "paid",
    ]
    list_filter = ["paid", "pickup_on_camp", "delivery_state"]
    search_fields = ["first_name", "last_name", "serial_number"]
    inlines = [OrderItemInline]
