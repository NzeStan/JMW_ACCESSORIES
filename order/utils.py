# order/utils.py
from weasyprint import HTML, CSS
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
import logging
import os
from io import BytesIO
from django.http import HttpResponse
from django.db.models import Count, Sum
from django.contrib.contenttypes.models import ContentType
from collections import defaultdict
from products.models import NyscTour, NyscKit, Church


logger = logging.getLogger(__name__)


def generate_receipt_pdf(orders, payment):
    """Generate PDF receipt for orders"""
    try:
        context = {
            "orders": orders,
            "payment": payment,
            "company_name": "JUME MEGA WEARS & ACCESSORIES",
            # "company_logo": "https://res.cloudinary.com/dhhaiy58r/image/upload/v1721420288/Black_White_Minimalist_Clothes_Store_Logo_e1o8ow.png",
            "company_email": settings.DEFAULT_FROM_EMAIL,
            "company_phone": "+2348071000804",
            "company_address": "16 Emejiaka Street, Ngwa Rd, Aba Abia State",
            "generated_date": payment.created,
        }

        # Render the HTML template
        html_string = render_to_string("order/receipt_pdf.html", context)

        # Create PDF without version specification
        html = HTML(string=html_string)
        return html.write_pdf()

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise


def send_receipt_email(email, pdf_content, reference):
    """Send receipt PDF via email"""
    try:
        subject = f"Your JMW Order Receipt - {reference}"
        message = f"""Thank you for your purchase at JUME MEGA WEARS & ACCESSORIES!

Your order has been successfully processed and paid for. Please find your receipt attached to this email.

Order Reference: {reference}

If you have any questions or concerns, please don't hesitate to contact us at contact@jumemegawears.com.

Best regards,
JUME MEGA WEARS & ACCESSORIES Team"""

        email_msg = EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [email])

        email_msg.attach(f"JMW_Receipt_{reference}.pdf", pdf_content, "application/pdf")

        email_msg.send()
        logger.info(f"Receipt email sent successfully for reference {reference}")

    except Exception as e:
        logger.error(f"Error sending receipt email: {str(e)}")
        raise

