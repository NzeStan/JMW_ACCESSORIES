from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from .models import Order
from payment.models import PaymentTransaction
from .utils import generate_receipt_pdf
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_receipt_email_task(payment_id):
    """
    Celery task to generate PDF receipt and send email.
    """
    try:
        payment = PaymentTransaction.objects.get(id=payment_id)
        orders = payment.orders.all()
        
        # Generate PDF
        pdf_content = generate_receipt_pdf(orders, payment)
        
        subject = f"Your JMW Order Receipt - {payment.reference}"
        message = f"""Thank you for your purchase at JUME MEGA WEARS & ACCESSORIES!

Your order has been successfully processed and paid for. Please find your receipt attached to this email.

Order Reference: {payment.reference}

If you have any questions or concerns, please don't hesitate to contact us at contact@jumemegawears.com.

Best regards,
JUME MEGA WEARS & ACCESSORIES Team"""

        email_msg = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [payment.email])
        email_msg.attach(f"JMW_Receipt_{payment.reference}.pdf", pdf_content, "application/pdf")
        email_msg.send()
        
        logger.info(f"Receipt email sent successfully via Celery for reference {payment.reference}")
        return f"Email sent for {payment.reference}"
        
    except PaymentTransaction.DoesNotExist:
        logger.error(f"PaymentTransaction with id {payment_id} not found.")
        return "Payment not found"
    except Exception as e:
        logger.error(f"Error in send_receipt_email_task: {str(e)}")
        raise e
