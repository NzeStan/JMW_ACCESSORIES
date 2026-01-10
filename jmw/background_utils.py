# jmw/background_utils.py
"""
Centralized background task and email utilities
Replaces Celery with lightweight threading and django-background-tasks
"""
from threading import Thread
from background_task import background
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# EMAIL UTILITIES (Using Threading for Quick Async)
# ============================================================================

def send_email_async(subject, message, from_email, recipient_list, attachments=None, html_message=None):
    """
    Send email asynchronously using threading.
    Use for quick email sends (confirmations, notifications).
    
    Args:
        subject: Email subject
        message: Plain text message
        from_email: Sender email
        recipient_list: List of recipient emails
        attachments: Optional list of (filename, content, mimetype) tuples
        html_message: Optional HTML version of message
    """
    def _send():
        try:
            if html_message:
                email = EmailMessage(subject, html_message, from_email, recipient_list)
                email.content_subtype = "html"
            else:
                email = EmailMessage(subject, message, from_email, recipient_list)
            
            if attachments:
                for filename, content, mimetype in attachments:
                    email.attach(filename, content, mimetype)
            
            email.send()
            logger.info(f"Email sent successfully: {subject} to {recipient_list}")
        except Exception as e:
            logger.error(f"Error sending email '{subject}' to {recipient_list}: {str(e)}")
    
    thread = Thread(target=_send)
    thread.daemon = True
    thread.start()
    logger.info(f"Email queued for async sending: {subject}")


def send_order_confirmation_email(order_entry):
    """Send order confirmation email after order creation"""
    context = {
        'order': order_entry,
        'bulk_order': order_entry.bulk_order,
        'company_name': settings.COMPANY_NAME,
    }
    
    html_message = render_to_string('bulk_orders/emails/order_confirmation.html', context)
    
    subject = f"Order Confirmation - {order_entry.bulk_order.organization_name}"
    
    send_email_async(
        subject=subject,
        message=f"Thank you for your order! Your order number is #{order_entry.serial_number}",
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order_entry.email]
    )


def send_payment_receipt_email(order_entry):
    """Send payment receipt email after successful payment"""
    context = {
        'order': order_entry,
        'bulk_order': order_entry.bulk_order,
        'company_name': settings.COMPANY_NAME,
        'company_address': settings.COMPANY_ADDRESS,
        'company_phone': settings.COMPANY_PHONE,
        'company_email': settings.COMPANY_EMAIL,
    }
    
    html_message = render_to_string('bulk_orders/emails/payment_receipt.html', context)
    
    subject = f"Payment Receipt - Order #{order_entry.serial_number}"
    
    send_email_async(
        subject=subject,
        message=f"Payment received for order #{order_entry.serial_number}",
        html_message=html_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order_entry.email]
    )


# ============================================================================
# BACKGROUND TASKS (Using django-background-tasks for Heavy Operations)
# ============================================================================

@background(schedule=0)
def generate_bulk_order_pdf_task(bulk_order_id, recipient_email):
    """
    Generate bulk order PDF in background and email it.
    Use for heavy PDF generation tasks.
    
    Args:
        bulk_order_id: UUID of the bulk order
        recipient_email: Email to send the PDF to
    """
    try:
        from bulk_orders.models import BulkOrderLink
        from django.db.models import Count, Q, Prefetch
        from bulk_orders.models import OrderEntry
        from django.utils import timezone
        from weasyprint import HTML
        
        bulk_order = BulkOrderLink.objects.prefetch_related(
            Prefetch(
                "orders",
                queryset=OrderEntry.objects.filter(paid=True).order_by("size", "full_name"),
            )
        ).get(id=bulk_order_id)
        
        orders = bulk_order.orders.all()
        size_summary = orders.values("size").annotate(count=Count("size")).order_by("size")
        
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
        
        # Send email with PDF attachment
        subject = f"Bulk Order Report - {bulk_order.organization_name}"
        message = f"Please find attached the bulk order report for {bulk_order.organization_name}."
        
        send_email_async(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            attachments=[
                (f'bulk_order_{bulk_order.slug}.pdf', pdf, 'application/pdf')
            ]
        )
        
        logger.info(f"Background PDF generation completed for bulk order: {bulk_order_id}")
        
    except Exception as e:
        logger.error(f"Error in background PDF generation: {str(e)}")


@background(schedule=0)
def generate_payment_receipt_pdf_task(order_entry_id):
    """Generate individual payment receipt PDF in background"""
    try:
        from bulk_orders.models import OrderEntry
        from weasyprint import HTML
        from django.utils import timezone
        
        order_entry = OrderEntry.objects.select_related('bulk_order', 'coupon_used').get(id=order_entry_id)
        
        context = {
            'order': order_entry,
            'bulk_order': order_entry.bulk_order,
            'company_name': settings.COMPANY_NAME,
            'company_address': settings.COMPANY_ADDRESS,
            'company_phone': settings.COMPANY_PHONE,
            'company_email': settings.COMPANY_EMAIL,
            'generated_date': timezone.now(),
        }
        
        html_string = render_to_string('bulk_orders/receipt_template.html', context)
        html = HTML(string=html_string)
        pdf = html.write_pdf()
        
        # Send receipt email with PDF
        subject = f"Payment Receipt - Order #{order_entry.serial_number}"
        message = f"Thank you for your payment! Please find your receipt attached."
        
        send_email_async(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order_entry.email],
            attachments=[
                (f'receipt_{order_entry.serial_number}.pdf', pdf, 'application/pdf')
            ]
        )
        
        logger.info(f"Payment receipt PDF generated for order entry: {order_entry_id}")

    except Exception as e:
        logger.error(f"Error generating payment receipt PDF: {str(e)}")


# ============================================================================
# ORDER APP - EMAIL & PDF TASKS
# ============================================================================

def send_order_confirmation_email_async(order_id):
    """
    Send order confirmation email after order creation (payment pending).
    Uses threading for quick async delivery.

    Args:
        order_id: UUID of the order
    """
    def _send():
        try:
            from order.models import Order

            order = Order.objects.select_related('user').prefetch_related('items').get(id=order_id)

            context = {
                'order': order,
                'company_name': settings.COMPANY_NAME,
                'company_address': settings.COMPANY_ADDRESS,
                'company_phone': settings.COMPANY_PHONE,
                'company_email': settings.COMPANY_EMAIL,
                'currency_symbol': settings.CURRENCY_SYMBOL,
                'frontend_url': settings.FRONTEND_URL,
            }

            html_message = render_to_string('order/order_confirmation_email.html', context)

            subject = settings.ORDER_CONFIRMATION_SUBJECT.format(reference=order.reference)

            email = EmailMessage(subject, html_message, settings.DEFAULT_FROM_EMAIL, [order.email])
            email.content_subtype = "html"
            email.send()

            logger.info(f"Order confirmation email sent for order: {order.reference}")

        except Exception as e:
            logger.error(f"Error sending order confirmation email for order_id {order_id}: {str(e)}")

    thread = Thread(target=_send)
    thread.daemon = True
    thread.start()
    logger.info(f"Order confirmation email queued for order_id: {order_id}")


@background(schedule=0)
def generate_order_confirmation_pdf_task(order_id):
    """
    Generate order confirmation PDF in background and email to customer.
    Heavy task - uses django-background-tasks.

    Args:
        order_id: UUID of the order
    """
    try:
        from order.models import Order
        from weasyprint import HTML
        from django.utils import timezone

        order = Order.objects.select_related('user').prefetch_related(
            'items__content_type',
            'items__content_object'
        ).get(id=order_id)

        context = {
            'order': order,
            'company_name': settings.COMPANY_NAME,
            'company_address': settings.COMPANY_ADDRESS,
            'company_phone': settings.COMPANY_PHONE,
            'company_email': settings.COMPANY_EMAIL,
            'currency_symbol': settings.CURRENCY_SYMBOL,
            'currency_code': settings.CURRENCY_CODE,
            'generated_date': timezone.now(),
        }

        html_string = render_to_string('order/order_confirmation_pdf.html', context)
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        filename = settings.PDF_FILENAME_ORDER_CONFIRMATION.format(
            company=settings.COMPANY_SHORT_NAME,
            reference=order.reference
        )

        # Send email with PDF attachment
        subject = settings.ORDER_CONFIRMATION_SUBJECT.format(reference=order.reference)
        message = f"Thank you for your order! Your order confirmation is attached."

        send_email_async(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            attachments=[(filename, pdf, 'application/pdf')]
        )

        logger.info(f"Order confirmation PDF generated and sent for order: {order.reference}")

    except Exception as e:
        logger.error(f"Error generating order confirmation PDF for order_id {order_id}: {str(e)}")


def send_payment_receipt_email_async(payment_id):
    """
    Send payment receipt email after payment verification.
    Uses threading for quick async delivery.

    Args:
        payment_id: UUID of the payment transaction
    """
    def _send():
        try:
            from payment.models import PaymentTransaction

            payment = PaymentTransaction.objects.select_related('order').get(id=payment_id)

            context = {
                'payment': payment,
                'order': payment.order,
                'company_name': settings.COMPANY_NAME,
                'company_address': settings.COMPANY_ADDRESS,
                'company_phone': settings.COMPANY_PHONE,
                'company_email': settings.COMPANY_EMAIL,
                'currency_symbol': settings.CURRENCY_SYMBOL,
                'frontend_url': settings.FRONTEND_URL,
            }

            html_message = render_to_string('order/payment_receipt_email.html', context)

            subject = settings.PAYMENT_RECEIPT_SUBJECT.format(reference=payment.reference)

            email = EmailMessage(subject, html_message, settings.DEFAULT_FROM_EMAIL, [payment.email])
            email.content_subtype = "html"
            email.send()

            logger.info(f"Payment receipt email sent for payment: {payment.reference}")

        except Exception as e:
            logger.error(f"Error sending payment receipt email for payment_id {payment_id}: {str(e)}")

    thread = Thread(target=_send)
    thread.daemon = True
    thread.start()
    logger.info(f"Payment receipt email queued for payment_id: {payment_id}")


@background(schedule=0)
def generate_payment_receipt_pdf_task(payment_id):
    """
    Generate payment receipt PDF in background and email to customer.
    Heavy task - uses django-background-tasks.

    Args:
        payment_id: UUID of the payment transaction
    """
    try:
        from payment.models import PaymentTransaction
        from weasyprint import HTML
        from django.utils import timezone

        payment = PaymentTransaction.objects.select_related('order').prefetch_related(
            'order__items__content_type',
            'order__items__content_object'
        ).get(id=payment_id)

        context = {
            'payment': payment,
            'order': payment.order,
            'company_name': settings.COMPANY_NAME,
            'company_address': settings.COMPANY_ADDRESS,
            'company_phone': settings.COMPANY_PHONE,
            'company_email': settings.COMPANY_EMAIL,
            'currency_symbol': settings.CURRENCY_SYMBOL,
            'currency_code': settings.CURRENCY_CODE,
            'generated_date': timezone.now(),
        }

        html_string = render_to_string('order/payment_receipt_pdf.html', context)
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        filename = settings.PDF_FILENAME_PAYMENT_RECEIPT.format(
            company=settings.COMPANY_SHORT_NAME,
            reference=payment.reference
        )

        # Send email with PDF attachment
        subject = settings.PAYMENT_RECEIPT_SUBJECT.format(reference=payment.reference)
        message = f"Payment received! Your receipt is attached."

        send_email_async(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[payment.email],
            attachments=[(filename, pdf, 'application/pdf')]
        )

        logger.info(f"Payment receipt PDF generated and sent for payment: {payment.reference}")

    except Exception as e:
        logger.error(f"Error generating payment receipt PDF for payment_id {payment_id}: {str(e)}")


@background(schedule=0)
def generate_admin_order_report_pdf_task(order_id, recipient_email):
    """
    Generate comprehensive order report for admin in background.
    Includes all order items, measurements, and customer details.

    Args:
        order_id: UUID of the order
        recipient_email: Admin email to send the report to
    """
    try:
        from order.models import Order
        from weasyprint import HTML
        from django.utils import timezone

        order = Order.objects.select_related('user').prefetch_related(
            'items__content_type',
            'items__content_object'
        ).get(id=order_id)

        context = {
            'order': order,
            'company_name': settings.COMPANY_NAME,
            'company_address': settings.COMPANY_ADDRESS,
            'company_phone': settings.COMPANY_PHONE,
            'company_email': settings.COMPANY_EMAIL,
            'currency_symbol': settings.CURRENCY_SYMBOL,
            'currency_code': settings.CURRENCY_CODE,
            'generated_date': timezone.now(),
        }

        # Use admin report template (could be more detailed)
        html_string = render_to_string('order/order_confirmation_pdf.html', context)
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        filename = f"{settings.COMPANY_SHORT_NAME}_Admin_Report_{order.reference}.pdf"

        # Send to admin
        subject = f"Admin Order Report - {order.reference}"
        message = f"Order report for {order.reference} is attached."

        send_email_async(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            attachments=[(filename, pdf, 'application/pdf')]
        )

        logger.info(f"Admin order report PDF generated for order: {order.reference}")

    except Exception as e:
        logger.error(f"Error generating admin order report for order_id {order_id}: {str(e)}")