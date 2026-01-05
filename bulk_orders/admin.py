# bulk_orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Count, Q, Prefetch
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.utils import timezone
from django.conf import settings
from io import BytesIO
import xlsxwriter
import logging
from .models import BulkOrderLink, OrderEntry, CouponCode
from .utils import (
    generate_coupon_codes,
    generate_bulk_order_pdf,
    generate_bulk_order_word,
    generate_bulk_order_excel,
)

logger = logging.getLogger(__name__)


class CouponCodeInline(admin.TabularInline):
    model = CouponCode
    extra = 0
    readonly_fields = ["code", "is_used", "created_at"]
    fields = ["code", "is_used", "created_at"]
    can_delete = False
    max_num = 0
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        """✅ FIX: Only show coupons for THIS bulk order"""
        qs = super().get_queryset(request)
        # The parent object (bulk_order) is automatically filtered
        return qs


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
        "custom_name_display",
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

    def custom_name_display(self, obj):
        """✅ FIX: Only show custom_name if bulk_order has custom_branding_enabled"""
        if obj.bulk_order.custom_branding_enabled and obj.custom_name:
            return obj.custom_name
        return format_html('<span style="color: gray;">-</span>')
    
    custom_name_display.short_description = "Custom Name"

    def paid_status(self, obj):
        if obj.paid:
            return format_html('<span style="color: green; font-weight: bold;">✔ Paid</span>')
        return format_html('<span style="color: red;">✘ Unpaid</span>')

    paid_status.short_description = "Payment Status"

    def coupon_status(self, obj):
        if obj.coupon_used:
            return format_html('<span style="color: blue; font-weight: bold;">🎟️ {}</span>', obj.coupon_used.code)
        return format_html('<span style="color: gray;">-</span>')

    coupon_status.short_description = "Coupon"

    def bulk_order_link(self, obj):
        url = reverse(
            "admin:bulk_orders_bulkorderlink_change", args=[obj.bulk_order.id]
        )
        return format_html('<a href="{}">{}</a>', url, obj.bulk_order.organization_name)

    bulk_order_link.short_description = "Bulk Order"
    
    def get_form(self, request, obj=None, **kwargs):
        """✅ FIX: Filter coupon_used dropdown to show ONLY coupons from the order's bulk_order"""
        form = super().get_form(request, obj, **kwargs)
        
        if obj and 'coupon_used' in form.base_fields:
            # Filter to show only coupons from THIS bulk order
            form.base_fields['coupon_used'].queryset = CouponCode.objects.filter(
                bulk_order=obj.bulk_order,
                is_used=False
            ) | CouponCode.objects.filter(id=obj.coupon_used_id) if obj.coupon_used else CouponCode.objects.filter(
                bulk_order=obj.bulk_order,
                is_used=False
            )
        
        return form


@admin.register(BulkOrderLink)
class BulkOrderLinkAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "organization_name",
        "slug_display",
        "price_per_item",
        "custom_branding_enabled",
        "payment_deadline",
        "total_orders",
        "total_paid",
        "coupon_count",
        "created_at",
    ]
    list_filter = ["custom_branding_enabled", "created_at", "payment_deadline"]
    search_fields = ["organization_name", "slug"]
    readonly_fields = ["created_at", "updated_at", "slug", "shareable_link"]
    list_per_page = 20
    actions = ['download_pdf_action', 'download_word_action', 'download_excel_action', 'generate_coupons_action']

    inlines = [CouponCodeInline]

    fieldsets = (
        ("Organization Details", {
            "fields": ("organization_name", "slug", "shareable_link", "created_by")
        }),
        ("Order Configuration", {
            "fields": ("price_per_item", "custom_branding_enabled", "payment_deadline")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def changelist_view(self, request, extra_context=None):
        """Store request for use in list_display methods"""
        self._request = request
        return super().changelist_view(request, extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Store request for use in readonly_fields methods"""
        self._request = request
        return super().change_view(request, object_id, form_url, extra_context)

    def slug_display(self, obj):
        return format_html('<code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px;">{}</code>', obj.slug)
    slug_display.short_description = "URL Slug"

    def shareable_link(self, obj):
        """Display the shareable link for easy copying"""
        if obj.slug:
            path = obj.get_shareable_url()
            
            if hasattr(self, '_request'):
                full_url = self._request.build_absolute_uri(path)
            else:
                full_url = path
            
            return format_html(
                '<input type="text" value="{}" readonly style="width: 100%; padding: 5px;" onclick="this.select();" /> '
                '<small style="color: #666;">Click to select and copy</small>',
                full_url
            )
        return "-"
    shareable_link.short_description = "Shareable Link"

    def total_orders(self, obj):
        count = obj.orders.count()
        if count > 0:
            return format_html('<strong>{}</strong>', count)
        return count
    total_orders.short_description = "Total Orders"

    def total_paid(self, obj):
        count = obj.orders.filter(paid=True).count()
        total = obj.orders.count()
        if total > 0:
            percentage = (count / total) * 100
            color = "#2ecc71" if percentage > 80 else "#f39c12" if percentage > 50 else "#e74c3c"
            percentage_str = f"{percentage:.0f}"
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} / {} ({}%)</span>',
                color, count, total, percentage_str
            )
        return "0 / 0"
    total_paid.short_description = "Paid Orders"

    def coupon_count(self, obj):
        total = obj.coupons.count()
        used = obj.coupons.filter(is_used=True).count()
        if total > 0:
            return format_html(
                '<span title="Used / Total">{} / {} <small style="color: #666;">used</small></span>',
                used, total
            )
        return format_html('<span style="color: #999;">No coupons</span>')
    coupon_count.short_description = "Coupons"

    # Admin Actions
    def download_pdf_action(self, request, queryset):
        """Generate PDF for selected bulk orders"""
        if queryset.count() > 1:
            self.message_user(request, "Please select only one bulk order for PDF generation.", messages.WARNING)
            return
        
        bulk_order = queryset.first()
        return self._generate_pdf(request, bulk_order)
    
    download_pdf_action.short_description = "📄 Download PDF"

    def download_word_action(self, request, queryset):
        """Generate Word document for selected bulk orders"""
        if queryset.count() > 1:
            self.message_user(request, "Please select only one bulk order for Word generation.", messages.WARNING)
            return
        
        bulk_order = queryset.first()
        return self._generate_word(request, bulk_order)
    
    download_word_action.short_description = "📝 Download Word"

    def download_excel_action(self, request, queryset):
        """Generate Excel for selected bulk orders"""
        if queryset.count() > 1:
            self.message_user(request, "Please select only one bulk order for Excel generation.", messages.WARNING)
            return
        
        bulk_order = queryset.first()
        return self._generate_excel(request, bulk_order)
    
    download_excel_action.short_description = "📊 Download Excel"

    def generate_coupons_action(self, request, queryset):
        """Generate coupons for selected bulk orders"""
        count = 0
        for bulk_order in queryset:
            if bulk_order.coupons.count() == 0:
                generate_coupon_codes(bulk_order, count=50)
                count += 1
        
        if count > 0:
            self.message_user(
                request,
                f"Successfully generated coupons for {count} bulk order(s).",
                messages.SUCCESS
            )
        else:
            self.message_user(
                request,
                "No bulk orders needed coupon generation (they already have coupons).",
                messages.WARNING
            )
    
    generate_coupons_action.short_description = "🎟️ Generate Coupons (50 per order)"

    def _generate_pdf(self, request, bulk_order):
        """Generate PDF using centralized utility"""
        try:
            return generate_bulk_order_pdf(bulk_order, request)
        except ImportError:
            messages.error(request, "PDF generation not available. Install GTK+ libraries.")
            return None
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            messages.error(request, f"Error generating PDF: {str(e)}")
            return None
        
    def _generate_word(self, request, bulk_order):
        """Generate Word document using centralized utility"""
        try:
            return generate_bulk_order_word(bulk_order)
        except Exception as e:
            logger.error(f"Error generating Word document: {str(e)}")
            messages.error(request, f"Error generating Word document: {str(e)}")
            return None

    def _generate_excel(self, request, bulk_order):
        """Generate Excel using centralized utility"""
        try:
            return generate_bulk_order_excel(bulk_order)
        except Exception as e:
            logger.error(f"Error generating Excel: {str(e)}")
            messages.error(request, f"Error generating Excel: {str(e)}")
            return None


@admin.register(CouponCode)
class CouponCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'bulk_order_link', 'is_used', 'created_at']
    list_filter = ['is_used', 'bulk_order', 'created_at']
    search_fields = ['code', 'bulk_order__organization_name']
    readonly_fields = ['code', 'created_at']
    ordering = ['-created_at']
    
    def bulk_order_link(self, obj):
        url = reverse("admin:bulk_orders_bulkorderlink_change", args=[obj.bulk_order.id])
        return format_html('<a href="{}">{}</a>', url, obj.bulk_order.organization_name)
    bulk_order_link.short_description = "Bulk Order"

    def has_add_permission(self, request):
        return False