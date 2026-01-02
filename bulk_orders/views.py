from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import BulkOrderLink, OrderEntry, CouponCode
from .serializers import BulkOrderLinkSerializer, OrderEntrySerializer, CouponCodeSerializer
from .utils import generate_receipt
import logging

logger = logging.getLogger(__name__)

class BulkOrderLinkViewSet(viewsets.ModelViewSet):
    serializer_class = BulkOrderLinkSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = BulkOrderLink.objects.all()

    def get_queryset(self):
        if self.request.user.is_staff:
             return BulkOrderLink.objects.all()
        # For public view, maybe filter by active? or just return all?
        # Assuming creators can see their own, and public can view via ID (DetailView).
        # For list, maybe only own?
        if self.request.user.is_authenticated:
            return BulkOrderLink.objects.filter(created_by=self.request.user)
        return BulkOrderLink.objects.none() # Or public links logic
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def download_pdf(self, request, pk=None):
        """Generate PDF summary for bulk order"""
        try:
            # Lazy import to avoid startup errors on Windows without Cairo
            from weasyprint import HTML
            from django.template.loader import render_to_string
            
            bulk_order = self.get_object()
            orders = bulk_order.orders.all()
            
            context = {
                'bulk_order': bulk_order,
                'orders': orders,
                'organization': bulk_order.organization_name,
            }
            
            html_string = render_to_string('bulk_orders/pdf_template.html', context)
            html = HTML(string=html_string)
            pdf = html.write_pdf()
            
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="bulk_order_{bulk_order.organization_name}.pdf"'
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
    def download_word(self, request, pk=None):
        """Generate Word document for bulk order"""
        try:
            from docx import Document
            from io import BytesIO
            
            bulk_order = self.get_object()
            orders = bulk_order.orders.all()
            
            # Create document
            doc = Document()
            doc.add_heading(f'Bulk Order: {bulk_order.organization_name}', 0)
            
            # Add table
            table = doc.add_table(rows=1, cols=5)
            table.style = 'Light Grid Accent 1'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Serial'
            hdr_cells[1].text = 'Name'
            hdr_cells[2].text = 'Email'
            hdr_cells[3].text = 'Size'
            hdr_cells[4].text = 'Custom Name'
            
            for order in orders:
                row_cells = table.add_row().cells
                row_cells[0].text = str(order.serial_number)
                row_cells[1].text = order.full_name
                row_cells[2].text = order.email
                row_cells[3].text = order.size
                row_cells[4].text = order.custom_name or '-'
            
            # Save to BytesIO
            file_stream = BytesIO()
            doc.save(file_stream)
            file_stream.seek(0)
            
            response = HttpResponse(
                file_stream.read(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="bulk_order_{bulk_order.organization_name}.docx"'
            return response
            
        except Exception as e:
            logger.error(f"Error generating Word document: {str(e)}")
            return Response(
                {"error": f"Error generating Word document: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def generate_size_summary(self, request, pk=None):
        """Generate Excel size summary for bulk order"""
        try:
            import xlsxwriter
            from io import BytesIO
            from django.db.models import Count
            
            bulk_order = self.get_object()
            
            # Group orders by size
            size_summary = bulk_order.orders.values('size').annotate(
                count=Count('id')
            ).order_by('size')
            
            # Create Excel file
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet('Size Summary')
            
            # Add headers
            bold = workbook.add_format({'bold': True})
            worksheet.write('A1', 'Size', bold)
            worksheet.write('B1', 'Count', bold)
            
            # Add data
            row = 1
            for item in size_summary:
                worksheet.write(row, 0, item['size'])
                worksheet.write(row, 1, item['count'])
                row += 1
            
            workbook.close()
            output.seek(0)
            
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="size_summary_{bulk_order.organization_name}.xlsx"'
            return response
            
        except Exception as e:
            logger.error(f"Error generating Excel: {str(e)}")
            return Response(
                {"error": f"Error generating Excel: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderEntryViewSet(viewsets.ModelViewSet):
    serializer_class = OrderEntrySerializer
    permission_classes = [permissions.AllowAny] # Allow public to submit orders?
    
    def get_queryset(self):
        # Users might want to see their own orders if authenticated
        if self.request.user.is_authenticated:
            return OrderEntry.objects.filter(email=self.request.user.email)
        return OrderEntry.objects.none()

    def perform_create(self, serializer):
        # Public creation logic is handled in serializer
        serializer.save()

class CouponCodeViewSet(viewsets.ModelViewSet):
    serializer_class = CouponCodeSerializer
    permission_classes = [permissions.IsAdminUser] # Only admin/staff manage coupons?
    queryset = CouponCode.objects.all()