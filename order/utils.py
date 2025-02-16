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
            "company_logo": "https://res.cloudinary.com/dhhaiy58r/image/upload/v1721420288/Black_White_Minimalist_Clothes_Store_Logo_e1o8ow.png",
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


def generate_nysc_tour_pdf(queryset, state=None):
    """Generate PDF for NYSC Tour orders."""
    # Filter by state if provided
    if state:
        content_type = ContentType.objects.get_for_model(NyscTour)
        queryset = queryset.filter(
            items__content_type=content_type, items__product__name=state, paid=True
        )

    # Prepare data
    orders_data = []
    counter = 1
    total_participants = 0

    for order in queryset:
        for item in order.items.all():
            if item.content_type == ContentType.objects.get_for_model(NyscTour):
                orders_data.append(
                    {
                        "sn": counter,
                        "full_name": f"{order.first_name} {order.middle_name} {order.last_name}".strip(),
                        "state": item.product.name,
                        "call_up_number": item.extra_fields.get(
                            "call_up_number", "N/A"
                        ),
                    }
                )
                counter += 1
                total_participants += item.quantity

    # Prepare summary data
    summary = {
        "total_participants": total_participants,
        "states_breakdown": defaultdict(int),
    }

    for order in orders_data:
        summary["states_breakdown"][order["state"]] += 1

    # Render PDF
    html_string = render_to_string(
        "orders/nysc_tour_pdf.html",
        {"orders": orders_data, "summary": summary, "selected_state": state},
    )

    html = HTML(string=html_string)
    return html.write_pdf()


def generate_church_pdf(queryset, church=None):
    """Generate PDF for Church orders."""
    if church:
        content_type = ContentType.objects.get_for_model(Church)
        queryset = queryset.filter(
            items__content_type=content_type, items__product__church=church, paid=True
        )

    orders_data = []
    counter = 1
    summary = defaultdict(lambda: defaultdict(int))

    for order in queryset:
        for item in order.items.all():
            if item.content_type == ContentType.objects.get_for_model(Church):
                orders_data.append(
                    {
                        "sn": counter,
                        "full_name": f"{order.first_name} {order.middle_name} {order.last_name}".strip(),
                        "church": item.product.church,
                        "quantity": item.quantity,
                        "size": item.extra_fields.get("size", "N/A"),
                        "pickup_on_camp": order.pickup_on_camp,
                        "delivery_state": (
                            order.delivery_state if not order.pickup_on_camp else "N/A"
                        ),
                        "delivery_lga": (
                            order.delivery_lga if not order.pickup_on_camp else "N/A"
                        ),
                    }
                )
                counter += 1

                # Update summary
                summary[item.product.church]["total_quantity"] += item.quantity
                summary[item.product.church]["sizes"][
                    item.extra_fields.get("size", "N/A")
                ] += item.quantity
                if order.pickup_on_camp:
                    summary[item.product.church]["pickup"] += item.quantity
                else:
                    summary[item.product.church]["delivery"] += item.quantity

    html_string = render_to_string(
        "orders/church_pdf.html",
        {"orders": orders_data, "summary": dict(summary), "selected_church": church},
    )

    html = HTML(string=html_string)
    return html.write_pdf()


def generate_nysc_kit_pdf(queryset, state=None):
    """Generate PDF for NYSC Kit orders."""
    if state:
        queryset = queryset.filter(state=state, paid=True)

    orders_data = []
    measurements_data = []
    counter = 1
    summary = defaultdict(lambda: defaultdict(int))

    for order in queryset:
        for item in order.items.all():
            if item.content_type == ContentType.objects.get_for_model(NyscKit):
                order_info = {
                    "sn": counter,
                    "full_name": f"{order.first_name} {order.middle_name} {order.last_name}".strip(),
                    "state_code": order.state_code,
                    "state": order.state,
                    "local_government": order.local_government,
                    "product_name": item.product.name,
                    "type": item.product.type,
                    "size": item.extra_fields.get("size", "N/A"),
                    "quantity": item.quantity,
                }

                orders_data.append(order_info)

                # If it's a khaki item, add measurements
                if item.product.type == "kakhi":
                    measurements = item.extra_fields.get("measurements", {})
                    if measurements:
                        measurements_data.append(
                            {
                                "sn": counter,
                                "full_name": order_info["full_name"],
                                "measurements": measurements,
                            }
                        )

                counter += 1
                summary[item.product.type]["total_quantity"] += item.quantity
                summary[item.product.type]["sizes"][
                    item.extra_fields.get("size", "N/A")
                ] += item.quantity

    html_string = render_to_string(
        "orders/nysc_kit_pdf.html",
        {
            "orders": orders_data,
            "measurements": measurements_data,
            "summary": dict(summary),
            "selected_state": state,
        },
    )

    html = HTML(string=html_string)
    return html.write_pdf()
