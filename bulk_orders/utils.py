# bulk_orders/utils.py
import string
import random
import logging
from django.utils import timezone
from .models import CouponCode
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from django.http import HttpResponse
from django.core.mail import EmailMessage
import os

logger = logging.getLogger(__name__)


def generate_coupon_codes(bulk_order, count=10):
    """Generate unique coupon codes for a bulk order."""
    chars = string.ascii_uppercase + string.digits
    codes = []
    try:
        for _ in range(count):
            while True:
                code = "".join(random.choices(chars, k=8))
                if not CouponCode.objects.filter(code=code).exists():
                    coupon = CouponCode.objects.create(bulk_order=bulk_order, code=code)
                    codes.append(coupon)
                    break
        logger.info(f"Generated {count} coupon codes for bulk order: {bulk_order.id}")
        return codes
    except Exception as e:
        logger.error(f"Error generating coupon codes: {str(e)}")
        raise

def generate_receipt(order):
    """Generate and send PDF receipt for an order."""
    try:
        # Prepare context for receipt template
        context = {
            "order": order,
            "bulk_order": order.bulk_order,
            "company_name": "JUME MEGA WEARS & ACCESSORIES",
            "company_address": settings.COMPANY_ADDRESS,
            "company_phone": settings.COMPANY_PHONE,
            "company_email": settings.COMPANY_EMAIL,
        }

        # Render receipt HTML
        html_string = render_to_string("bulk_orders/receipt.html", context)

        # Create PDF using WeasyPrint
        html = HTML(string=html_string)
        pdf_file = html.write_pdf()

        # Prepare and send email with PDF attachment
        subject = f"Order Receipt - {order.id}"
        message = f"Thank you for your order. Please find your receipt attached."
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [order.email]

        email = EmailMessage(
            subject=subject, body=message, from_email=from_email, to=recipient_list
        )

        # Attach PDF to email
        email.attach(
            filename=f"receipt-{order.id}.pdf",
            content=pdf_file,
            mimetype="application/pdf",
        )

        # Send email
        email.send()

        logger.info(f"Receipt generated and sent for order {order.id}")
        return True

    except Exception as e:
        logger.error(f"Error generating receipt for order {order.id}: {str(e)}")
        raise
