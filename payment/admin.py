from django.contrib import admin
from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ["reference", "amount", "email", "status", "created"]
    list_filter = ["status", "created"]
    search_fields = ["reference", "email"]
    readonly_fields = ["reference", "created", "modified", "orders"]

    fieldsets = (
        (None, {"fields": ("reference", "amount", "email", "status")}),
        (
            "Order Information",
            {"fields": ("orders",), "description": "Related orders for this payment"},
        ),
        ("Timestamps", {"fields": ("created", "modified"), "classes": ("collapse",)}),
    )
