# bulk_orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Count
from io import BytesIO
import xlsxwriter
import logging
from .models import BulkOrderLink, OrderEntry, CouponCode

logger = logging.getLogger(__name__)


class CouponCodeInline(admin.TabularInline):
    model = CouponCode
    extra = 0  # Don't show extra empty forms
    readonly_fields = ["created_at"]
    fields = ["code", "is_used", "created_at"]
    can_delete = False  # Prevent deletion from inline
    max_num = 0  # Don't allow adding through inline
    show_change_link = True


class HasCouponFilter(admin.SimpleListFilter):
    title = "Coupon Status"
    parameter_name = "has_coupon"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Has Coupon"),
            ("no", "No Coupon"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(coupon_used__isnull=False)
        if self.value() == "no":
            return queryset.filter(coupon_used__isnull=True)


@admin.register(OrderEntry)
class OrderEntryAdmin(admin.ModelAdmin):
    list_display = [
        "serial_number",
        "full_name",
        "email",
        "size",
        "custom_name",
        "bulk_order_link",
        "paid_status",
        "coupon_status",
        "created_at",
    ]
    list_filter = [
        "paid",
        "size",
        "bulk_order",
        HasCouponFilter,
    ]
    search_fields = ["full_name", "email", "custom_name"]
    readonly_fields = ["created_at", "updated_at", "serial_number"]
    ordering = ["bulk_order", "serial_number"]
    list_per_page = 20

    def paid_status(self, obj):
        if obj.paid:
            return format_html('<span style="color: green;">✔</span>')
        return format_html('<span style="color: red;">✘</span>')

    paid_status.short_description = "Paid"

    def coupon_status(self, obj):
        if obj.coupon_used:
            return format_html('<span style="color: blue;">Used</span>')
        return "-"

    coupon_status.short_description = "Coupon"

    def bulk_order_link(self, obj):
        url = reverse(
            "admin:bulk_orders_bulkorderlink_change", args=[obj.bulk_order.id]
        )
        return format_html('<a href="{}">{}</a>', url, obj.bulk_order.organization_name)

    bulk_order_link.short_description = "Bulk Order"


@admin.register(BulkOrderLink)
class BulkOrderLinkAdmin(admin.ModelAdmin):
    list_display = [
        "organization_name",
        "price_per_item",
        "custom_branding_enabled",
        "payment_deadline",
        "total_orders",
        "total_paid",
        "created_at",
        "download_buttons",
    ]
    list_filter = ["custom_branding_enabled", "created_at"]
    search_fields = ["organization_name"]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 20

    actions = ["download_word_doc", "download_pdf", "generate_size_summary"]

    inlines = [CouponCodeInline]

    def total_orders(self, obj):
        return obj.orders.count()

    total_orders.short_description = "Total Orders"

    def total_paid(self, obj):
        return obj.orders.filter(paid=True).count()

    total_paid.short_description = "Paid Orders"

    def download_buttons(self, obj):
        """Generate download buttons with consistent styling."""
        button_style = """
            display: inline-block;
            background-color: {color};
            color: white;
            padding: 5px 10px;
            text-decoration: none;
            border-radius: 3px;
            margin-right: 5px;
        """

        pdf_url = reverse("bulk_orders:download_pdf", args=[obj.id])
        word_url = reverse("bulk_orders:download_word", args=[obj.id])
        excel_url = reverse("bulk_orders:generate_size_summary", args=[obj.id])

        buttons = f"""
            <a class="button" href="{pdf_url}" target="_blank" 
               style="{button_style.format(color='#3498db')}">PDF</a>
            <a class="button" href="{word_url}" target="_blank" 
               style="{button_style.format(color='#2ecc71')}">Word</a>
            <a class="button" href="{excel_url}" target="_blank" 
               style="{button_style.format(color='#f1c40f')}">Excel</a>
        """
        return format_html(buttons.strip())

    download_buttons.short_description = "Downloads"

    def download_word_doc(self, request, queryset):
        """Generate Word documents for selected bulk orders."""
        try:
            response = HttpResponse(content_type="application/msword")
            response["Content-Disposition"] = 'attachment; filename="bulk_orders.doc"'
            # Implement actual Word document generation here
            return response
        except Exception as e:
            logger.error(f"Error generating Word documents: {str(e)}")
            self.message_user(request, "Error generating Word documents", level="ERROR")

    download_word_doc.short_description = "Download Word Documents"

    def download_pdf(self, request, queryset):
        """Generate PDFs for selected bulk orders."""
        try:
            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="bulk_orders.pdf"'
            # Implement actual PDF generation here
            return response
        except Exception as e:
            logger.error(f"Error generating PDFs: {str(e)}")
            self.message_user(request, "Error generating PDFs", level="ERROR")

    download_pdf.short_description = "Download PDFs"

    def generate_size_summary(self, request, queryset):
        """Generate Excel summary for selected bulk orders."""
        try:
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="size_summary.xlsx"'
            # Implement actual Excel generation here
            return response
        except Exception as e:
            logger.error(f"Error generating Excel summary: {str(e)}")
            self.message_user(request, "Error generating Excel summary", level="ERROR")

    generate_size_summary.short_description = "Generate Size Summary"

