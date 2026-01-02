from django.db import models
from django.db.models import Count, Sum
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from rest_framework import views, permissions, status
from rest_framework.response import Response

from order.models import OrderItem
from measurement.models import Measurement
from products.models import NyscTour, Church, NyscKit
from products.constants import STATES, CHURCH_CHOICES

User = get_user_model()


class NyscKitPDFView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    template_name = "orderitem_generation/nysckit_state_template.html"

    def get_context(self, request):
        state = request.GET.get("state")
        if not state:
            return None

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
            return None

        # Get all kakhi orders and their measurements
        kakhi_measurements = []
        counter = 1  # To match with the order details numbering
        for order_item in order_items:
            if (
                order_item.content_type == nysc_kit_type
                and order_item.product.type == "kakhi"
            ):
                try:
                    # Find user by email from order
                    user = User.objects.get(email=order_item.order.email)
                    measurement = (
                        Measurement.objects.filter(user=user)
                        .order_by("-created_at")
                        .first()
                    )  # Get the most recent measurement
                    if measurement:
                        kakhi_measurements.append(
                            {
                                "counter": counter,
                                "name": f"{order_item.order.last_name} {order_item.order.first_name}",
                                "measurement": measurement,
                            }
                        )
                except User.DoesNotExist:
                    # Handle case where user doesn't exist
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

        # Product-level summary (across all LGAs)
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

        # Process both summaries to include product names
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
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context(request)
        if context is None:
            return Response(
                {"error": "Please select a state or no orders found for the selected state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lazy import to avoid startup errors on Windows without Cairo
        try:
            import weasyprint
        except ImportError:
            return Response(
                {"error": "PDF generation not available. WeasyPrint requires GTK+ libraries."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        html = render_to_string(self.template_name, context)
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Order_{context["state"]}.pdf"'
        )
        weasyprint.HTML(string=html).write_pdf(response)

        return response


class NyscTourPDFView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    template_name = "orderitem_generation/nysctour_state_template.html"

    def get_context(self, request):
        state = request.GET.get("state")
        if not state:
            return None

        # Get content type and product IDs in a single query
        nysc_tour_type = ContentType.objects.get_for_model(NyscTour)
        tour_ids = NyscTour.objects.filter(name=state).values_list("id", flat=True)

        # Filter order items in a single query
        order_items = OrderItem.objects.select_related("order", "content_type").filter(
            order__paid=True, content_type=nysc_tour_type, object_id__in=tour_ids
        )

        if not order_items.exists():
            return None

        context = {
            "state": state,
            "order_items": order_items,
        }
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context(request)
        if context is None:
            return Response(
                {"error": "Please select a state or no orders found for the selected state"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Lazy import to avoid startup errors on Windows without Cairo
        try:
            import weasyprint
        except ImportError:
            return Response(
                {"error": "PDF generation not available. WeasyPrint requires GTK+ libraries."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        html = render_to_string(self.template_name, context)
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Order_{context["state"]}.pdf"'
        )
        weasyprint.HTML(string=html).write_pdf(response)

        return response


class ChurchPDFView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    template_name = "orderitem_generation/church_state_template.html"

    def get_context(self, request):
        church = request.GET.get("church")
        if not church:
            return None

        church_type = ContentType.objects.get_for_model(Church)
        church_ids = Church.objects.filter(church=church).values_list("id", flat=True)

        # Get the queryset without ordering
        order_items = OrderItem.objects.select_related(
            "order", "content_type"
        ).filter(order__paid=True, content_type=church_type, object_id__in=church_ids)

        if not order_items.exists():
            return None

        # Convert to list and sort in Python
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

        # Sort summary data
        sorted_summary = sorted(
            summary_data.values(), key=lambda x: (x["product_name"], x["size"])
        )

        # Calculate totals
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
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context(request)
        if context is None:
            return Response(
                {"error": "Please select a church or no orders found for the selected church"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Lazy import to avoid startup errors on Windows without Cairo
        try:
            import weasyprint
        except ImportError:
            return Response(
                {"error": "PDF generation not available. WeasyPrint requires GTK+ libraries."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        html = render_to_string(self.template_name, context)
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Order_{context["church"]}.pdf"'
        )
        weasyprint.HTML(string=html).write_pdf(response)

        return response