# order/utils.py
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def generate_receipt_pdf(orders, payment):
    """Generate PDF receipt for orders"""
    try:
        # Lazy import to avoid startup errors on Windows without Cairo
        from weasyprint import HTML
        
        context = {
            "orders": orders,
            "payment": payment,
            "company_name": settings.COMPANY_NAME,
            "company_email": settings.COMPANY_EMAIL,
            "company_phone": settings.COMPANY_PHONE,
            "company_address": settings.COMPANY_ADDRESS,
            "generated_date": payment.created,
        }

        # Render the HTML template
        html_string = render_to_string("order/receipt_pdf.html", context)

        # Create PDF
        html = HTML(string=html_string)
        return html.write_pdf()

    except ImportError as e:
        logger.error(f"WeasyPrint not available: {str(e)}. Install GTK+ libraries for PDF generation.")
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise


def send_receipt_email(email, pdf_content, reference):
    """Send receipt PDF via email"""
    try:
        subject = f"Your JMW Order Receipt - {reference}"
        message = f"""Thank you for your purchase at {settings.COMPANY_NAME}!

Your order has been successfully processed and paid for. Please find your receipt attached to this email.

Order Reference: {reference}

If you have any questions or concerns, please don't hesitate to contact us at {settings.CONTACT_EMAIL}.

Best regards,
{settings.COMPANY_NAME} Team"""

        email_msg = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        email_msg.attach(f"JMW_Receipt_{reference}.pdf", pdf_content, "application/pdf")
        email_msg.send()
        
        logger.info(f"Receipt email sent successfully for reference {reference}")

    except Exception as e:
        logger.error(f"Error sending receipt email: {str(e)}")
        raise