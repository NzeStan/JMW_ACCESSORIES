from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import BulkOrderLink, OrderEntry, CouponCode
from .serializers import BulkOrderLinkSerializer, OrderEntrySerializer, CouponCodeSerializer
from .utils import generate_receipt, generate_coupon_codes
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class BulkOrderLinkViewSet(viewsets.ModelViewSet):
    serializer_class = BulkOrderLinkSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = BulkOrderLink.objects.all()
    lookup_field = 'slug'  # Use slug instead of pk for lookups

    def get_queryset(self):
        if self.request.user.is_staff:
             return BulkOrderLink.objects.all()
        # For public view, maybe filter by active? or just return all?
        # Assuming creators can see their own, and public can view via slug (DetailView).
        # For list, maybe only own?
        if self.request.user.is_authenticated:
            return BulkOrderLink.objects.filter(created_by=self.request.user)
        return BulkOrderLink.objects.none() # Or public links logic
    
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
                "sample_codes": [c.code for c in coupons[:5]]  # Return first 5 as sample
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
            # Lazy import to avoid startup errors on Windows without Cairo
            from weasyprint import HTML
            from django.template.loader import render_to_string
            
            bulk_order = self.get_object()
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
            response['Content-Disposition'] = f'attachment; filename="bulk_order_{bulk_order.slug}.pdf"'
            
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
            
            bulk_order = self.get_object()
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
            response['Content-Disposition'] = f'attachment; filename="bulk_order_{bulk_order.slug}.docx"'
            
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
            from django.db.models import Count
            
            bulk_order = self.get_object()
            
            # Group orders by size for this bulk order only
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
            worksheet.write('A3', f'Paid Orders: {bulk_order.orders.filter(paid=True).count()}')
            worksheet.write('A4', '')
            
            # Add headers
            worksheet.write('A5', 'Size', bold)
            worksheet.write('B5', 'Count', bold)
            worksheet.write('C5', 'Percentage', bold)
            
            # Add data
            row = 5
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
            response['Content-Disposition'] = f'attachment; filename="size_summary_{bulk_order.slug}.xlsx"'
            
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
    permission_classes = [permissions.AllowAny] # Allow public to submit orders
    
    def get_queryset(self):
        # Users might want to see their own orders if authenticated
        if self.request.user.is_authenticated:
            return OrderEntry.objects.filter(email=self.request.user.email).select_related('bulk_order', 'coupon_used')
        return OrderEntry.objects.none()

    def perform_create(self, serializer):
        # Public creation logic is handled in serializer
        serializer.save()


class CouponCodeViewSet(viewsets.ModelViewSet):
    serializer_class = CouponCodeSerializer
    permission_classes = [permissions.IsAdminUser] # Only admin/staff manage coupons
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