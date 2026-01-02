from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Prefetch
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from .models import BulkOrderLink, OrderEntry, CouponCode
from .serializers import BulkOrderLinkSerializer, OrderEntrySerializer, CouponCodeSerializer
from .utils import generate_receipt, generate_coupon_codes
import logging

logger = logging.getLogger(__name__)


class BulkOrderLinkViewSet(viewsets.ModelViewSet):
    serializer_class = BulkOrderLinkSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = BulkOrderLink.objects.all()
    lookup_field = 'slug'

    def get_queryset(self):
        if self.request.user.is_staff:
             return BulkOrderLink.objects.all()
        if self.request.user.is_authenticated:
            return BulkOrderLink.objects.filter(created_by=self.request.user)
        return BulkOrderLink.objects.none()
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def generate_coupons(self, request, slug=None):
        """Generate coupons for a bulk order"""
        bulk_order = self.get_object()
        count = request.data.get('count', 50)
        
        if bulk_order.coupons.count() > 0:
            return Response(
                {"error": f"This bulk order already has {bulk_order.coupons.count()} coupons."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            coupons = generate_coupon_codes(bulk_order, count=count)
            return Response({
                "message": f"Successfully generated {len(coupons)} coupons",
                "count": len(coupons),
                "sample_codes": [c.code for c in coupons[:5]]
            })
        except Exception as e:
            logger.error(f"Error generating coupons: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def download_pdf(self, request, slug=None):
        """Generate PDF summary for this specific bulk order"""
        try:
            from weasyprint import HTML
            
            # Optimized query
            bulk_order = BulkOrderLink.objects.prefetch_related(
                Prefetch(
                    "orders",
                    queryset=OrderEntry.objects.select_related("coupon_used")
                    .filter(Q(paid=True) | Q(coupon_used__isnull=False))
                    .order_by("size", "full_name"),
                )
            ).get(slug=slug)
            
            orders = bulk_order.orders.all()
            
            # Size summary
            size_summary = (
                orders.values("size")
                .annotate(count=Count("size"))
                .order_by("size")
            )
            
            context = {
                'bulk_order': bulk_order,
                'size_summary': size_summary,
                'orders': orders,
                'total_orders': orders.count(),
                'company_name': settings.COMPANY_NAME,
                'company_address': settings.COMPANY_ADDRESS,
                'company_phone': settings.COMPANY_PHONE,
                'company_email': settings.COMPANY_EMAIL,
                'now': timezone.now(),
            }
            
            html_string = render_to_string('bulk_orders/pdf_template.html', context)
            html = HTML(string=html_string)
            pdf = html.write_pdf()
            
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f'bulk_order_{bulk_order.slug}_{timezone.now().strftime("%Y%m%d")}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Generated PDF for bulk order: {bulk_order.slug}")
            return response
            
        except ImportError:
            return Response(
                {"error": "PDF generation not available. Install GTK+ libraries."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return Response(
                {"error": f"Error generating PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def download_word(self, request, slug=None):
        """Generate Word document for this specific bulk order"""
        try:
            from docx import Document
            from io import BytesIO
            
            # Optimized query
            bulk_order = BulkOrderLink.objects.prefetch_related(
                Prefetch(
                    "orders",
                    queryset=OrderEntry.objects.select_related("coupon_used")
                    .filter(Q(paid=True) | Q(coupon_used__isnull=False))
                    .order_by("size", "full_name"),
                )
            ).get(slug=slug)
            
            doc = Document()
            
            # Header
            doc.add_heading(settings.COMPANY_NAME, 0)
            doc.add_heading(f'Bulk Order: {bulk_order.organization_name}', level=1)
            doc.add_paragraph(f"Generated: {timezone.now().strftime('%B %d, %Y - %I:%M %p')}")
            doc.add_paragraph(f'Price per Item: ₦{bulk_order.price_per_item:,.2f}')
            doc.add_paragraph(f'Payment Deadline: {bulk_order.payment_deadline.strftime("%B %d, %Y")}')
            doc.add_paragraph('')
            
            orders = bulk_order.orders.all()
            
            # Size Summary
            doc.add_heading('Summary by Size', level=2)
            size_summary = (
                orders.values("size")
                .annotate(
                    total=Count("id"),
                    paid=Count("id", filter=Q(paid=True)),
                    coupon=Count("id", filter=Q(coupon_used__isnull=False)),
                )
                .order_by("size")
            )
            
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Light Grid Accent 1'
            header_cells = table.rows[0].cells
            header_cells[0].text = 'Size'
            header_cells[1].text = 'Total'
            header_cells[2].text = 'Paid'
            header_cells[3].text = 'Coupon'
            
            for size_info in size_summary:
                row_cells = table.add_row().cells
                row_cells[0].text = size_info['size']
                row_cells[1].text = str(size_info['total'])
                row_cells[2].text = str(size_info['paid'])
                row_cells[3].text = str(size_info['coupon'])
            
            doc.add_paragraph()
            
            # Orders by Size
            paginator = Paginator(orders, 1000)
            
            for page_num in paginator.page_range:
                page = paginator.page(page_num)
                
                size_groups = {}
                for order in page.object_list:
                    if order.size not in size_groups:
                        size_groups[order.size] = []
                    size_groups[order.size].append(order)
                
                for size, size_orders in sorted(size_groups.items()):
                    doc.add_heading(f'Size: {size}', level=3)
                    
                    table = doc.add_table(rows=1, cols=4)
                    table.style = 'Table Grid'
                    header_cells = table.rows[0].cells
                    header_cells[0].text = 'S/N'
                    header_cells[1].text = 'Name'
                    header_cells[2].text = 'Custom Name' if bulk_order.custom_branding_enabled else ''
                    header_cells[3].text = 'Status'
                    
                    for idx, order in enumerate(size_orders, 1):
                        row_cells = table.add_row().cells
                        row_cells[0].text = str(idx)
                        row_cells[1].text = order.full_name
                        row_cells[2].text = order.custom_name or ''
                        row_cells[3].text = 'Coupon' if order.coupon_used else 'Paid'
                    
                    doc.add_paragraph()
            
            # Footer
            doc.add_paragraph("")
            footer_para = doc.add_paragraph()
            footer_para.add_run(f"{settings.COMPANY_NAME}\n").bold = True
            footer_para.add_run(f"{settings.COMPANY_ADDRESS}\n")
            footer_para.add_run(f"📞 {settings.COMPANY_PHONE} | 📧 {settings.COMPANY_EMAIL}")
            
            file_stream = BytesIO()
            doc.save(file_stream)
            file_stream.seek(0)
            
            response = HttpResponse(
                file_stream.read(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            filename = f'bulk_order_{bulk_order.slug}_{timezone.now().strftime("%Y%m%d")}.docx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Generated Word document for bulk order: {bulk_order.slug}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating Word document: {str(e)}")
            return Response(
                {"error": f"Error generating Word document: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def generate_size_summary(self, request, slug=None):
        """Generate Excel size summary for this specific bulk order"""
        try:
            import xlsxwriter
            from io import BytesIO
            
            # Optimized query
            bulk_order = BulkOrderLink.objects.prefetch_related(
                Prefetch(
                    "orders",
                    queryset=OrderEntry.objects.select_related("coupon_used")
                    .filter(Q(paid=True) | Q(coupon_used__isnull=False))
                    .order_by("size", "full_name"),
                )
            ).get(slug=slug)
            
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'constant_memory': True})
            
            # Formats
            header_format = workbook.add_format(
                {'bold': True, 'bg_color': '#f0f0f0', 'border': 1, 'align': 'center'}
            )
            cell_format = workbook.add_format({'border': 1, 'align': 'center'})
            title_format = workbook.add_format({'bold': True, 'font_size': 14})
            
            worksheet = workbook.add_worksheet(bulk_order.organization_name[:31])
            
            # Title
            worksheet.write(0, 0, f"{settings.COMPANY_NAME}", title_format)
            worksheet.write(1, 0, f"Bulk Order: {bulk_order.organization_name}", title_format)
            worksheet.write(2, 0, f"Generated: {timezone.now().strftime('%B %d, %Y')}")
            
            # Headers
            headers = ['S/N', 'Size', 'Name', 'Custom Name', 'Status']
            for col, header in enumerate(headers):
                worksheet.write(4, col, header, header_format)
            
            # Orders
            row = 5
            chunk_size = 1000
            orders = bulk_order.orders.all()
            
            for i in range(0, orders.count(), chunk_size):
                order_chunk = orders[i : i + chunk_size]
                
                for order in order_chunk:
                    worksheet.write(row, 0, row - 4, cell_format)
                    worksheet.write(row, 1, order.size, cell_format)
                    worksheet.write(row, 2, order.full_name, cell_format)
                    worksheet.write(row, 3, order.custom_name or '', cell_format)
                    worksheet.write(
                        row, 4, 'Coupon' if order.coupon_used else 'Paid', cell_format
                    )
                    row += 1
            
            # Size Summary
            summary_row = row + 2
            worksheet.merge_range(
                summary_row, 0, summary_row, 4, 'Size Summary', header_format
            )
            
            summary_headers = ['Size', 'Total', 'Paid', 'Coupon']
            summary_row += 1
            for col, header in enumerate(summary_headers):
                worksheet.write(summary_row, col, header, header_format)
            
            size_summary = (
                orders.values("size")
                .annotate(
                    total=Count("id"),
                    paid=Count("id", filter=Q(paid=True)),
                    coupon=Count("id", filter=Q(coupon_used__isnull=False)),
                )
                .order_by("size")
            )
            
            for size_data in size_summary:
                summary_row += 1
                worksheet.write(summary_row, 0, size_data['size'], cell_format)
                worksheet.write(summary_row, 1, size_data['total'], cell_format)
                worksheet.write(summary_row, 2, size_data['paid'], cell_format)
                worksheet.write(summary_row, 3, size_data['coupon'], cell_format)
            
            # Column widths
            worksheet.set_column(0, 0, 5)
            worksheet.set_column(1, 1, 10)
            worksheet.set_column(2, 2, 30)
            worksheet.set_column(3, 3, 30)
            worksheet.set_column(4, 4, 15)
            
            workbook.close()
            output.seek(0)
            
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'bulk_order_{bulk_order.slug}_{timezone.now().strftime("%Y%m%d")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            logger.info(f"Generated Excel for bulk order: {bulk_order.slug}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating Excel: {str(e)}")
            return Response(
                {"error": f"Error generating Excel: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def stats(self, request, slug=None):
        """Get statistics for this specific bulk order"""
        bulk_order = self.get_object()
        total_orders = bulk_order.orders.count()
        paid_orders = bulk_order.orders.filter(paid=True).count()
        
        return Response({
            'organization': bulk_order.organization_name,
            'slug': bulk_order.slug,
            'total_orders': total_orders,
            'paid_orders': paid_orders,
            'unpaid_orders': total_orders - paid_orders,
            'payment_percentage': (paid_orders / total_orders * 100) if total_orders > 0 else 0,
            'total_coupons': bulk_order.coupons.count(),
            'used_coupons': bulk_order.coupons.filter(is_used=True).count(),
            'is_expired': bulk_order.is_expired(),
            'payment_deadline': bulk_order.payment_deadline,
        })


class OrderEntryViewSet(viewsets.ModelViewSet):
    serializer_class = OrderEntrySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return OrderEntry.objects.filter(email=self.request.user.email).select_related('bulk_order', 'coupon_used')
        return OrderEntry.objects.none()

    def perform_create(self, serializer):
        serializer.save()


class CouponCodeViewSet(viewsets.ModelViewSet):
    serializer_class = CouponCodeSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = CouponCode.objects.all().select_related('bulk_order')
    
    @action(detail=True, methods=['post'])
    def validate_coupon(self, request, pk=None):
        """Validate if a coupon is valid and unused"""
        coupon = self.get_object()
        
        if coupon.is_used:
            return Response({
                "valid": False,
                "message": "This coupon has already been used."
            })
        
        return Response({
            "valid": True,
            "code": coupon.code,
            "bulk_order": coupon.bulk_order.organization_name,
            "bulk_order_slug": coupon.bulk_order.slug,
        })