# bulk_orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.http import HttpResponse
from django.db.models import Count
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.template.loader import render_to_string
from io import BytesIO
import xlsxwriter
import logging
from .models import BulkOrderLink, OrderEntry, CouponCode
from .utils import generate_coupon_codes

logger = logging.getLogger(__name__)


class CouponCodeInline(admin.TabularInline):
    model = CouponCode
    extra = 0  # Don't show extra empty forms
    readonly_fields = ["code", "is_used", "created_at"]
    fields = ["code", "is_used", "created_at"]
    can_delete = False  # Prevent deletion from inline
    max_num = 0  # Don't allow adding through inline
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        # Disable adding coupons via inline
        return False


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


@admin.register(BulkOrderLink)
class BulkOrderLinkAdmin(admin.ModelAdmin):
    list_display = [
        "organization_name",
        "slug_display",
        "price_per_item",
        "custom_branding_enabled",
        "payment_deadline",
        "total_orders",
        "total_paid",
        "coupon_count",
        "created_at",
        "action_buttons",
    ]
    list_filter = ["custom_branding_enabled", "created_at", "payment_deadline"]
    search_fields = ["organization_name", "slug"]
    readonly_fields = ["created_at", "updated_at", "slug", "shareable_link"]
    list_per_page = 20
    actions = ['generate_coupons_action']

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
        """Display the shareable link for easy copying - dynamically built from current request"""
        if obj.slug:
            path = obj.get_shareable_url()
            
            # Build absolute URI from current request (stored in changelist_view/change_view)
            if hasattr(self, '_request'):
                full_url = self._request.build_absolute_uri(path)
            else:
                # Fallback if request not available (shouldn't happen)
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
            # Format percentage first, then pass to format_html
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

    def action_buttons(self, obj):
        """Generate action buttons for downloads and coupon generation"""
        base_style = "display:inline-block;color:white;padding:6px 12px;text-decoration:none;border-radius:4px;margin-right:5px;margin-bottom:5px;font-size:11px;font-weight:bold;"

        buttons = []

        # Download buttons
        pdf_url = reverse("admin:bulk_orders_download_pdf", args=[obj.id])
        buttons.append(f'<a href="{pdf_url}" target="_blank" style="{base_style}background-color:#3498db;">📄 PDF</a>')

        word_url = reverse("admin:bulk_orders_download_word", args=[obj.id])
        buttons.append(f'<a href="{word_url}" target="_blank" style="{base_style}background-color:#2ecc71;">📝 Word</a>')

        excel_url = reverse("admin:bulk_orders_download_excel", args=[obj.id])
        buttons.append(f'<a href="{excel_url}" target="_blank" style="{base_style}background-color:#f39c12;">📊 Excel</a>')

        # Coupon generation button
        if obj.coupons.count() == 0:
            coupon_url = reverse("admin:bulk_orders_generate_coupons", args=[obj.id])
            buttons.append(f'<a href="{coupon_url}" style="{base_style}background-color:#9b59b6;">🎟️ Generate Coupons</a>')

        return format_html("".join(buttons))

    action_buttons.short_description = "Actions"

    def generate_coupons_action(self, request, queryset):
        """Admin action to generate coupons for selected bulk orders"""
        count = 0
        for bulk_order in queryset:
            if bulk_order.coupons.count() == 0:
                # Default to 50 coupons, can be customized
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
    
    generate_coupons_action.short_description = "Generate coupons (50 per order)"

    def get_urls(self):
        """Add custom admin URLs for download actions and coupon generation"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:object_id>/download-pdf/',
                self.admin_site.admin_view(self.download_pdf_view),
                name='bulk_orders_download_pdf',
            ),
            path(
                '<uuid:object_id>/download-word/',
                self.admin_site.admin_view(self.download_word_view),
                name='bulk_orders_download_word',
            ),
            path(
                '<uuid:object_id>/download-excel/',
                self.admin_site.admin_view(self.download_excel_view),
                name='bulk_orders_download_excel',
            ),
            path(
                '<uuid:object_id>/generate-coupons/',
                self.admin_site.admin_view(self.generate_coupons_view),
                name='bulk_orders_generate_coupons',
            ),
        ]
        return custom_urls + urls

    def download_pdf_view(self, request, object_id):
        """Generate PDF for a specific bulk order"""
        try:
            # Lazy import to avoid startup errors on Windows without Cairo
            from weasyprint import HTML
            
            bulk_order = get_object_or_404(BulkOrderLink, id=object_id)
            orders = bulk_order.orders.all().select_related('coupon_used')
            
            context = {
                'bulk_order': bulk_order,
                'orders': orders,
                'organization': bulk_order.organization_name,
                'now': timezone.now(),
            }
            
            html_string = render_to_string('bulk_orders/pdf_template.html', context)
            html = HTML(string=html_string)
            pdf = html.write_pdf()
            
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f'bulk_order_{bulk_order.slug}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Generated PDF for bulk order: {bulk_order.slug}")
            return response
            
        except ImportError:
            messages.error(request, "PDF generation not available. Install GTK+ libraries.")
            return redirect('admin:bulk_orders_bulkorderlink_change', object_id)
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            messages.error(request, f"Error generating PDF: {str(e)}")
            return redirect('admin:bulk_orders_bulkorderlink_change', object_id)

    def download_word_view(self, request, object_id):
        """Generate Word document for a specific bulk order"""
        try:
            from docx import Document
            
            bulk_order = get_object_or_404(BulkOrderLink, id=object_id)
            orders = bulk_order.orders.all().select_related('coupon_used')
            
            # Create document
            doc = Document()
            doc.add_heading(f'Bulk Order: {bulk_order.organization_name}', 0)
            doc.add_paragraph(f'Price per Item: ₦{bulk_order.price_per_item:,.2f}')
            doc.add_paragraph(f'Payment Deadline: {bulk_order.payment_deadline.strftime("%B %d, %Y")}')
            doc.add_paragraph(f'Total Orders: {orders.count()}')
            doc.add_paragraph('')
            
            # Add table
            table = doc.add_table(rows=1, cols=6)
            table.style = 'Light Grid Accent 1'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Serial'
            hdr_cells[1].text = 'Name'
            hdr_cells[2].text = 'Email'
            hdr_cells[3].text = 'Size'
            hdr_cells[4].text = 'Custom Name'
            hdr_cells[5].text = 'Paid'
            
            for order in orders:
                row_cells = table.add_row().cells
                row_cells[0].text = str(order.serial_number)
                row_cells[1].text = order.full_name
                row_cells[2].text = order.email
                row_cells[3].text = order.size
                row_cells[4].text = order.custom_name or '-'
                row_cells[5].text = '✓' if order.paid else '✗'
            
            # Save to BytesIO
            file_stream = BytesIO()
            doc.save(file_stream)
            file_stream.seek(0)
            
            response = HttpResponse(
                file_stream.read(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            filename = f'bulk_order_{bulk_order.slug}.docx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Generated Word document for bulk order: {bulk_order.slug}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating Word document: {str(e)}")
            messages.error(request, f"Error generating Word document: {str(e)}")
            return redirect('admin:bulk_orders_bulkorderlink_change', object_id)

    def download_excel_view(self, request, object_id):
        """Generate Excel size summary for a specific bulk order"""
        try:
            bulk_order = get_object_or_404(BulkOrderLink, id=object_id)
            
            # Group orders by size
            size_summary = bulk_order.orders.values('size').annotate(
                count=Count('id')
            ).order_by('size')
            
            # Create Excel file
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet('Size Summary')
            
            # Add formats
            bold = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2'})
            title_format = workbook.add_format({'bold': True, 'font_size': 14})
            
            # Add title
            worksheet.write('A1', f'Size Summary: {bulk_order.organization_name}', title_format)
            worksheet.write('A2', f'Total Orders: {bulk_order.orders.count()}')
            worksheet.write('A3', '')
            
            # Add headers
            worksheet.write('A4', 'Size', bold)
            worksheet.write('B4', 'Count', bold)
            worksheet.write('C4', 'Percentage', bold)
            
            # Add data
            row = 4
            total_orders = bulk_order.orders.count()
            for item in size_summary:
                percentage = (item['count'] / total_orders * 100) if total_orders > 0 else 0
                worksheet.write(row, 0, item['size'])
                worksheet.write(row, 1, item['count'])
                worksheet.write(row, 2, f"{percentage:.1f}%")
                row += 1
            
            # Adjust column widths
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 12)
            worksheet.set_column('C:C', 15)
            
            workbook.close()
            output.seek(0)
            
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'size_summary_{bulk_order.slug}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Generated Excel for bulk order: {bulk_order.slug}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating Excel: {str(e)}")
            messages.error(request, f"Error generating Excel: {str(e)}")
            return redirect('admin:bulk_orders_bulkorderlink_change', object_id)

    def generate_coupons_view(self, request, object_id):
        """Generate coupons for a specific bulk order"""
        bulk_order = get_object_or_404(BulkOrderLink, id=object_id)
        
        if bulk_order.coupons.count() > 0:
            messages.warning(request, f"Bulk order '{bulk_order.organization_name}' already has {bulk_order.coupons.count()} coupons.")
        else:
            try:
                # Generate 50 coupons by default
                coupons = generate_coupon_codes(bulk_order, count=50)
                messages.success(
                    request,
                    f"Successfully generated {len(coupons)} coupons for '{bulk_order.organization_name}'."
                )
            except Exception as e:
                logger.error(f"Error generating coupons: {str(e)}")
                messages.error(request, f"Error generating coupons: {str(e)}")
        
        return redirect('admin:bulk_orders_bulkorderlink_change', object_id)


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
        # Prevent manual addition - coupons should be generated via action
        return False