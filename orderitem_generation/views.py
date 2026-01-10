from django.db import models
from django.db.models import Count, Sum
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import views, permissions, status
from rest_framework.response import Response
from background_task import background
from jmw.background_utils import send_email_async
import logging

from order.models import OrderItem
from measurement.models import Measurement
from products.models import NyscTour, Church, NyscKit
from products.constants import STATES, CHURCH_CHOICES

User = get_user_model()
logger = logging.getLogger(__name__)


@background(schedule=0)
def generate_nysc_kit_pdf_task(state, recipient_email):
    """
    Background task to generate NYSC Kit PDF report and email to admin.

    Args:
        state: State code to filter orders
        recipient_email: Email to send the PDF to
    """
    try:
        from weasyprint import HTML

        # Get ContentType for NyscKit
        nysc_kit_type = ContentType.objects.get_for_model(NyscKit)

        # Filter for orders of type NyscKitOrder with matching state
        order_items = (
            OrderItem.objects.select_related(
                "order",
                "content_type",
            )
            .filter(order__paid=True, order__delivery_details__state=state)
            .order_by(
                "order__delivery_details__local_government",
                "content_type",
                "object_id",
                "extra_fields__size",
            )
        )

        if not order_items.exists():
            logger.warning(f"No orders found for state: {state}")
            return

        # Get all kakhi orders and their measurements
        kakhi_measurements = []
        counter = 1
        for order_item in order_items:
            if (
                order_item.content_type == nysc_kit_type
                and order_item.product.type == "kakhi"
            ):
                try:
                    user = User.objects.get(email=order_item.order.email)
                    measurement = (
                        Measurement.objects.select_related("user")
                        .filter(user=user)
                        .order_by("-created_at")
                        .first()
                    )
                    if measurement:
                        kakhi_measurements.append(
                            {
                                "counter": counter,
                                "name": f"{order_item.order.last_name} {order_item.order.first_name}",
                                "measurement": measurement,
                            }
                        )
                except User.DoesNotExist:
                    pass
            counter += 1

        totals = order_items.aggregate(
            grand_total_count=Count("id"), grand_total_sum=Sum("quantity")
        )

        # LGA-level summary
        summary_query = (
            order_items.values(
                "content_type",
                "object_id",
                "extra_fields__size",
                "order__delivery_details__local_government",
            )
            .annotate(
                total_count=Count("id"),
                total_sum=Sum("quantity"),
            )
            .order_by(
                "order__delivery_details__local_government",
                "content_type",
                "object_id",
                "extra_fields__size",
            )
        )

        # Product-level summary
        product_summary_query = (
            order_items.values("content_type", "object_id", "extra_fields__size")
            .annotate(
                total_count=Count("id"),
                total_sum=Sum("quantity"),
            )
            .order_by(
                "content_type",
                "object_id",
                "extra_fields__size",
            )
        )

        # Process summaries
        processed_summary = []
        for item in summary_query:
            order_item = order_items.filter(
                content_type=item["content_type"], object_id=item["object_id"]
            ).first()

            if order_item:
                processed_item = {
                    "product__name": (
                        order_item.product.name if order_item.product else ""
                    ),
                    "extra_fields__size": item["extra_fields__size"],
                    "order__local_government": item[
                        "order__delivery_details__local_government"
                    ],
                    "total_count": item["total_count"],
                    "total_sum": item["total_sum"],
                }
                processed_summary.append(processed_item)

        processed_product_summary = []
        for item in product_summary_query:
            order_item = order_items.filter(
                content_type=item["content_type"], object_id=item["object_id"]
            ).first()

            if order_item:
                processed_item = {
                    "product__name": (
                        order_item.product.name if order_item.product else ""
                    ),
                    "extra_fields__size": item["extra_fields__size"],
                    "total_count": item["total_count"],
                    "total_sum": item["total_sum"],
                }
                processed_product_summary.append(processed_item)

        context = {
            "state": state,
            "order_items": order_items,
            "summary_query": processed_summary,
            "product_summary": processed_product_summary,
            "grand_total_count": totals["grand_total_count"],
            "grand_total_sum": totals["grand_total_sum"],
            "kakhi_measurements": kakhi_measurements,
        }

        # Generate PDF
        html_string = render_to_string("orderitem_generation/nysckit_state_template.html", context)
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        filename = f"{settings.COMPANY_SHORT_NAME}_NYSC_Kit_Order_{state}.pdf"

        # Send email with PDF attachment
        subject = f"NYSC Kit Order Report - {state}"
        message = f"Please find attached the NYSC Kit order report for {state}."

        send_email_async(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            attachments=[(filename, pdf, 'application/pdf')]
        )

        logger.info(f"NYSC Kit PDF generated and sent for state: {state}")

    except Exception as e:
        logger.error(f"Error generating NYSC Kit PDF for state {state}: {str(e)}")


@background(schedule=0)
def generate_nysc_tour_pdf_task(state, recipient_email):
    """
    Background task to generate NYSC Tour PDF report and email to admin.

    Args:
        state: State name to filter orders
        recipient_email: Email to send the PDF to
    """
    try:
        from weasyprint import HTML

        nysc_tour_type = ContentType.objects.get_for_model(NyscTour)
        tour_ids = NyscTour.objects.filter(name=state).values_list("id", flat=True)

        order_items = OrderItem.objects.select_related("order", "content_type").filter(
            order__paid=True, content_type=nysc_tour_type, object_id__in=tour_ids
        )

        if not order_items.exists():
            logger.warning(f"No tour orders found for state: {state}")
            return

        context = {
            "state": state,
            "order_items": order_items,
        }

        # Generate PDF
        html_string = render_to_string("orderitem_generation/nysctour_state_template.html", context)
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        filename = f"{settings.COMPANY_SHORT_NAME}_NYSC_Tour_Order_{state}.pdf"

        # Send email with PDF attachment
        subject = f"NYSC Tour Order Report - {state}"
        message = f"Please find attached the NYSC Tour order report for {state}."

        send_email_async(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            attachments=[(filename, pdf, 'application/pdf')]
        )

        logger.info(f"NYSC Tour PDF generated and sent for state: {state}")

    except Exception as e:
        logger.error(f"Error generating NYSC Tour PDF for state {state}: {str(e)}")


@background(schedule=0)
def generate_church_pdf_task(church, recipient_email):
    """
    Background task to generate Church order PDF report and email to admin.

    Args:
        church: Church name to filter orders
        recipient_email: Email to send the PDF to
    """
    try:
        from weasyprint import HTML

        church_type = ContentType.objects.get_for_model(Church)
        church_ids = Church.objects.filter(church=church).values_list("id", flat=True)

        order_items = OrderItem.objects.select_related(
            "order", "content_type"
        ).filter(order__paid=True, content_type=church_type, object_id__in=church_ids)

        if not order_items.exists():
            logger.warning(f"No church orders found for: {church}")
            return

        # Convert to list and sort
        order_items_list = list(order_items)
        order_items_list.sort(
            key=lambda x: (
                x.product.name,
                x.extra_fields.get("size", ""),
                x.order.delivery_details.get("pickup_on_camp"),
            )
        )

        # Create summary data
        summary_data = {}
        for item in order_items_list:
            product_name = item.product.name
            size = item.extra_fields.get("size", "N/A")
            key = (product_name, size)

            if key not in summary_data:
                summary_data[key] = {
                    "product_name": product_name,
                    "size": size,
                    "total_quantity": 0,
                    "pickup_count": 0,
                    "delivery_count": 0,
                }

            summary_data[key]["total_quantity"] += item.quantity
            if item.order.delivery_details.get("pickup_on_camp"):
                summary_data[key]["pickup_count"] += item.quantity
            else:
                summary_data[key]["delivery_count"] += item.quantity

        sorted_summary = sorted(
            summary_data.values(), key=lambda x: (x["product_name"], x["size"])
        )

        totals = {
            "total_quantity": sum(item["total_quantity"] for item in sorted_summary),
            "pickup_count": sum(item["pickup_count"] for item in sorted_summary),
            "delivery_count": sum(item["delivery_count"] for item in sorted_summary),
        }

        context = {
            "church": church,
            "order_items": order_items_list,
            "summary_data": sorted_summary,
            "totals": totals,
        }

        # Generate PDF
        html_string = render_to_string("orderitem_generation/church_state_template.html", context)
        html = HTML(string=html_string)
        pdf = html.write_pdf()

        filename = f"{settings.COMPANY_SHORT_NAME}_Church_Order_{church}.pdf"

        # Send email with PDF attachment
        subject = f"Church Order Report - {church}"
        message = f"Please find attached the church order report for {church}."

        send_email_async(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            attachments=[(filename, pdf, 'application/pdf')]
        )

        logger.info(f"Church PDF generated and sent for: {church}")

    except Exception as e:
        logger.error(f"Error generating Church PDF for {church}: {str(e)}")


class NyscKitPDFView(views.APIView):
    """
    API endpoint for NYSC Kit PDF report generation.
    Queues background task and returns immediate response.
    PDF is emailed to the admin user.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        state = request.GET.get("state")
        if not state:
            return Response(
                {"error": "Please provide a state parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get admin user email
        recipient_email = request.user.email

        # Queue background task
        try:
            generate_nysc_kit_pdf_task(state, recipient_email)
            logger.info(f"NYSC Kit PDF task queued for state: {state}, recipient: {recipient_email}")

            return Response({
                "status": "success",
                "message": f"PDF generation queued for {state}. You will receive an email at {recipient_email} once ready."
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Failed to queue NYSC Kit PDF task: {str(e)}")
            return Response(
                {"error": "Failed to queue PDF generation task"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NyscTourPDFView(views.APIView):
    """
    API endpoint for NYSC Tour PDF report generation.
    Queues background task and returns immediate response.
    PDF is emailed to the admin user.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        state = request.GET.get("state")
        if not state:
            return Response(
                {"error": "Please provide a state parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get admin user email
        recipient_email = request.user.email

        # Queue background task
        try:
            generate_nysc_tour_pdf_task(state, recipient_email)
            logger.info(f"NYSC Tour PDF task queued for state: {state}, recipient: {recipient_email}")

            return Response({
                "status": "success",
                "message": f"PDF generation queued for {state}. You will receive an email at {recipient_email} once ready."
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Failed to queue NYSC Tour PDF task: {str(e)}")
            return Response(
                {"error": "Failed to queue PDF generation task"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChurchPDFView(views.APIView):
    """
    API endpoint for Church order PDF report generation.
    Queues background task and returns immediate response.
    PDF is emailed to the admin user.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        church = request.GET.get("church")
        if not church:
            return Response(
                {"error": "Please provide a church parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get admin user email
        recipient_email = request.user.email

        # Queue background task
        try:
            generate_church_pdf_task(church, recipient_email)
            logger.info(f"Church PDF task queued for: {church}, recipient: {recipient_email}")

            return Response({
                "status": "success",
                "message": f"PDF generation queued for {church}. You will receive an email at {recipient_email} once ready."
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            logger.error(f"Failed to queue Church PDF task: {str(e)}")
            return Response(
                {"error": "Failed to queue PDF generation task"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
