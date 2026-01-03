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
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import uuid
from .models import BulkOrderLink, OrderEntry, CouponCode
from .serializers import BulkOrderLinkSerializer, OrderEntrySerializer, CouponCodeSerializer
from .utils import generate_receipt, generate_coupon_codes
from payment.utils import initialize_payment, verify_payment
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
                    
                    # ✅ FIX: Conditionally show Custom Name column
                    col_count = 4 if bulk_order.custom_branding_enabled else 3
                    table = doc.add_table(rows=1, cols=col_count)
                    table.style = 'Table Grid'
                    header_cells = table.rows[0].cells
                    header_cells[0].text = 'S/N'
                    header_cells[1].text = 'Name'
                    if bulk_order.custom_branding_enabled:
                        header_cells[2].text = 'Custom Name'
                        header_cells[3].text = 'Status'
                    else:
                        header_cells[2].text = 'Status'
                    
                    for idx, order in enumerate(size_orders, 1):
                        row_cells = table.add_row().cells
                        row_cells[0].text = str(idx)
                        row_cells[1].text = order.full_name
                        if bulk_order.custom_branding_enabled:
                            row_cells[2].text = order.custom_name or ''
                            row_cells[3].text = 'Coupon' if order.coupon_used else 'Paid'
                        else:
                            row_cells[2].text = 'Coupon' if order.coupon_used else 'Paid'
                    
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
            
            # ✅ FIX: Conditionally include Custom Name column
            headers = ['S/N', 'Size', 'Name']
            if bulk_order.custom_branding_enabled:
                headers.append('Custom Name')
            headers.append('Status')
            
            for col, header in enumerate(headers):
                worksheet.write(4, col, header, header_format)
            
            # Orders
            row = 5
            chunk_size = 1000
            orders = bulk_order.orders.all()
            
            for i in range(0, orders.count(), chunk_size):
                order_chunk = orders[i : i + chunk_size]
                
                for order in order_chunk:
                    col = 0
                    worksheet.write(row, col, row - 4, cell_format)
                    col += 1
                    worksheet.write(row, col, order.size, cell_format)
                    col += 1
                    worksheet.write(row, col, order.full_name, cell_format)
                    col += 1
                    
                    if bulk_order.custom_branding_enabled:
                        worksheet.write(row, col, order.custom_name or '', cell_format)
                        col += 1
                    
                    worksheet.write(
                        row, col, 'Coupon' if order.coupon_used else 'Paid', cell_format
                    )
                    row += 1
            
            # Size Summary
            summary_row = row + 2
            worksheet.merge_range(
                summary_row, 0, summary_row, len(headers) - 1, 'Size Summary', header_format
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
            if bulk_order.custom_branding_enabled:
                worksheet.set_column(3, 3, 30)
                worksheet.set_column(4, 4, 15)
            else:
                worksheet.set_column(3, 3, 15)
            
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
    """
    ViewSet for OrderEntry with improved UX:
    - No need to pass bulk_order_slug in request body
    - Slug is extracted from URL path
    """
    serializer_class = OrderEntrySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return OrderEntry.objects.filter(email=self.request.user.email).select_related('bulk_order', 'coupon_used')
        return OrderEntry.objects.none()

    def get_serializer_context(self):
        """Pass bulk_order to serializer via context"""
        context = super().get_serializer_context()
        
        # ✅ FIX: Extract slug from URL and pass bulk_order in context
        slug = self.request.data.get('bulk_order_slug') or self.kwargs.get('bulk_order_slug')
        
        if slug:
            try:
                bulk_order = BulkOrderLink.objects.get(slug=slug)
                context['bulk_order'] = bulk_order
            except BulkOrderLink.DoesNotExist:
                pass
        
        return context

    def create(self, request, *args, **kwargs):
        """Override create to handle bulk_order_slug from request body"""
        # Extract slug from request data
        slug = request.data.get('bulk_order_slug')
        
        if not slug:
            return Response(
                {"error": "bulk_order_slug is required in request body"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate bulk order exists
        try:
            bulk_order = BulkOrderLink.objects.get(slug=slug)
        except BulkOrderLink.DoesNotExist:
            return Response(
                {"error": "Invalid bulk order link"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Pass bulk_order via context
        serializer = self.get_serializer(data=request.data, context={'bulk_order': bulk_order, 'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # ✅ NEW: Payment initialization endpoint
    @action(detail=True, methods=['post'])
    def initialize_payment(self, request, pk=None):
        """Initialize payment for an OrderEntry"""
        order_entry = self.get_object()
        
        # Check if already paid
        if order_entry.paid:
            return Response(
                {"error": "This order has already been paid"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate payment reference
        reference = f"ORDER-{order_entry.bulk_order.id}-{order_entry.id}"
        
        # Calculate amount
        amount = order_entry.bulk_order.price_per_item
        email = order_entry.email
        
        # Build callback URL
        callback_url = request.build_absolute_uri(f"/api/bulk_orders/payment/callback/")
        
        # Initialize payment
        result = initialize_payment(amount, email, reference, callback_url)
        
        if result and result.get('status'):
            return Response({
                "authorization_url": result['data']['authorization_url'],
                "access_code": result['data']['access_code'],
                "reference": reference
            })
        
        return Response(
            {"error": "Payment initialization failed"},
            status=status.HTTP_400_BAD_REQUEST
        )


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


# ✅ NEW: Payment webhook handler for bulk orders
@csrf_exempt
def bulk_order_payment_webhook(request):
    """
    Webhook handler for Paystack payment notifications for bulk orders
    Reference format: ORDER-{bulk_order_id}-{order_entry_id}
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)
    
    try:
        payload = json.loads(request.body)
        logger.info(f"Bulk order payment webhook received: {payload}")
        
        # Verify webhook is from Paystack
        event = payload.get('event')
        if event != 'charge.success':
            return JsonResponse({'status': 'ignored', 'message': 'Not a charge.success event'})
        
        data = payload.get('data', {})
        reference = data.get('reference')
        status_value = data.get('status')
        
        # Verify reference format: ORDER-{bulk_order_id}-{order_entry_id}
        if not reference or not reference.startswith('ORDER-'):
            return JsonResponse({'status': 'error', 'message': 'Invalid reference format'})
        
        # Extract IDs from reference
        try:
            parts = reference.split('-')
            bulk_order_id = parts[1]
            order_entry_id = parts[2]
        except (IndexError, ValueError):
            logger.error(f"Invalid reference format: {reference}")
            return JsonResponse({'status': 'error', 'message': 'Invalid reference format'})
        
        # Verify payment with Paystack
        verification_result = verify_payment(reference)
        
        if verification_result and verification_result.get('status') and verification_result['data']['status'] == 'success':
            # Update OrderEntry
            try:
                order_entry = OrderEntry.objects.get(id=order_entry_id, bulk_order__id=bulk_order_id)
                order_entry.paid = True
                order_entry.save()
                
                logger.info(f"Bulk order payment successful: {reference} - OrderEntry {order_entry_id} marked as paid")
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Payment verified and order updated',
                    'order_entry_id': str(order_entry_id)
                })
                
            except OrderEntry.DoesNotExist:
                logger.error(f"OrderEntry not found: {order_entry_id}")
                return JsonResponse({'status': 'error', 'message': 'Order entry not found'}, status=404)
        else:
            logger.warning(f"Payment verification failed for reference: {reference}")
            return JsonResponse({'status': 'error', 'message': 'Payment verification failed'}, status=400)
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing bulk order payment webhook: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)