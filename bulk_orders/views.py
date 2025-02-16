from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.utils import timezone
import uuid
from django.http import HttpResponse
from django.contrib import messages
import requests
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import Count, Q, Prefetch
from contextlib import contextmanager
import logging
import json
import hmac
import hashlib
from io import BytesIO
import xlsxwriter
from docx import Document
from docx.shared import Inches
from weasyprint import HTML

from .models import BulkOrderLink, OrderEntry, CouponCode
from .forms import BulkOrderLinkForm, OrderEntryForm
from .utils import generate_coupon_codes, generate_receipt
from payment.utils import get_paystack_keys

logger = logging.getLogger(__name__)


@contextmanager
def database_ops_optimizer():
    """Context manager for optimizing database operations."""
    try:
        yield
    finally:
        # Clear Django's SQL query cache
        connection.queries_log.clear()
        # Close the connection to free up resources
        connection.close()


@login_required
def generate_bulk_order(request):
    try:
        with database_ops_optimizer():
            if request.method == "POST":
                form = BulkOrderLinkForm(request.POST)
                if form.is_valid():
                    bulk_order = form.save(commit=False)
                    bulk_order.created_by = request.user

                    with transaction.atomic():
                        bulk_order.save()
                        generate_coupon_codes(bulk_order)

                    active_links = (
                        BulkOrderLink.objects.select_related("created_by")
                        .filter(
                            created_by=request.user, payment_deadline__gt=timezone.now()
                        )
                        .order_by("-created_at")
                    )

                    #messages.success(request, "Bulk order link generated successfully!")
                    return render(
                        request,
                        "bulk_orders/partials/links_container.html",
                        {"active_links": active_links, "request": request},
                    )
                else:
                    # Add error message for form validation failures
                    messages.error(request, "Please correct the errors below.")
                    return render(
                        request, "bulk_orders/partials/form.html", {"form": form}
                    )

            if request.htmx and request.GET.get("show_form"):
                return render(
                    request,
                    "bulk_orders/partials/form.html",
                    {"form": BulkOrderLinkForm()},
                )

            # Get all active links with optimized query
            active_links = (
                BulkOrderLink.objects.select_related("created_by")
                .prefetch_related(
                    Prefetch(
                        "orders",
                        queryset=OrderEntry.objects.select_related("coupon_used"),
                    )
                )
                .filter(created_by=request.user, payment_deadline__gt=timezone.now())
                .order_by("-created_at")
            )

            return render(
                request,
                "bulk_orders/generate.html",
                {"active_links": active_links, "form": BulkOrderLinkForm()},
            )

    except Exception as e:
        logger.error(f"Error in generate_bulk_order view: {str(e)}")
        messages.error(request, "An error occurred. Please try again.")
        return render(
            request,
            "bulk_orders/generate.html",
            {"form": BulkOrderLinkForm(), "error": str(e)},
        )


@csrf_protect
def copy_link(request, link_id):
    """Handle link copying notification."""
    try:
        messages.success(request, "Copied to clipboard!")
        return HttpResponse(status=200)
    except Exception as e:
        messages.error(request, "Failed to copy link.")
        return HttpResponse(status=500)


def order_landing_page(request, link_code):
    """Optimized order landing page view."""
    bulk_order = get_object_or_404(
        BulkOrderLink.objects.select_related("created_by").prefetch_related(
            Prefetch(
                "orders", queryset=OrderEntry.objects.select_related("coupon_used")
            )
        ),
        id=link_code,
    )

    if bulk_order.payment_deadline < timezone.now():
        return redirect("bulk_orders:link_expired")

    time_left = bulk_order.payment_deadline - timezone.now()
    days = time_left.days
    hours = int((time_left.seconds / 3600) % 24)
    minutes = int((time_left.seconds / 60) % 60)
    seconds = int(time_left.seconds % 60)

    context = {
        "bulk_order": bulk_order,
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
    }

    return render(request, "bulk_orders/order_landing.html", context)


def link_expired(request):
    """Handle expired links."""
    return render(request, "bulk_orders/link_expired.html")


def toggle_coupon_field(request):
    """Toggle coupon field visibility."""
    return render(request, "bulk_orders/partials/coupon_field.html")


def submit_order(request, link_code):
    """Handle order submission with optimized database operations."""
    if request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Method not allowed"}, status=405
        )

    try:
        with transaction.atomic():
            # Optimize query with select_related
            bulk_order = get_object_or_404(
                BulkOrderLink.objects.select_related("created_by"), id=link_code
            )
            form = OrderEntryForm(request.POST)

            if form.is_valid():
                order = form.save(commit=False)
                order.bulk_order = bulk_order

                # Handle coupon code with optimized query
                if form.cleaned_data.get("coupon_code"):
                    coupon = (
                        CouponCode.objects.select_related("bulk_order")
                        .filter(
                            bulk_order=bulk_order,
                            code=form.cleaned_data["coupon_code"],
                            is_used=False,
                        )
                        .first()
                    )

                    if coupon:
                        order.coupon_used = coupon
                        order.paid = True
                        order.save()

                        coupon.is_used = True
                        coupon.save()

                        try:
                            generate_receipt(order)
                        except Exception as e:
                            logger.error(f"Error generating receipt: {str(e)}")

                        return JsonResponse(
                            {
                                "status": "success",
                                "is_coupon": True,
                                "redirect_url": reverse(
                                    "bulk_orders:order_success", args=[order.id]
                                ),
                            }
                        )
                    else:
                        return JsonResponse(
                            {
                                "status": "error",
                                "message": "Invalid or already used coupon code",
                            }
                        )

                # Regular payment flow
                order.save()

                # Get Paystack keys
                secret_key, public_key = get_paystack_keys()

                # Create payment reference
                payment_reference = f"ORDER-{order.id}"

                # Prepare Paystack data
                payment_data = {
                    "email": order.email,
                    "amount": int(float(bulk_order.price_per_item) * 100),
                    "reference": payment_reference,
                    "callback_url": request.build_absolute_uri(
                        reverse("bulk_orders:order_success", args=[order.id])
                    ),
                    "metadata": {"order_id": str(order.id)},
                }

                return JsonResponse(
                    {
                        "status": "success",
                        "is_coupon": False,
                        "public_key": public_key,
                        "payment_data": payment_data,
                    }
                )
            else:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Invalid form data",
                        "errors": form.errors,
                    }
                )

    except Exception as e:
        logger.error(f"Error in submit_order: {str(e)}")
        return JsonResponse(
            {"status": "error", "message": "An error occurred processing your order"}
        )


def payment_verify(request, order_id):
    """Handle Paystack payment verification with optimized queries."""
    order = get_object_or_404(
        OrderEntry.objects.select_related("bulk_order", "coupon_used"), id=order_id
    )

    try:
        reference = request.GET.get("reference")
        if not reference:
            messages.error(request, "No reference provided")
            return redirect("bulk_orders:order_landing", link_code=order.bulk_order.id)

        secret_key, _ = get_paystack_keys()

        # Verify payment status with Paystack
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {secret_key}"},
        )

        if response.status_code == 200:
            response_data = response.json()

            if response_data["data"]["status"] == "success":
                with transaction.atomic():
                    order.paid = True
                    order.payment_reference = reference
                    order.save()

                    logger.info(f"Payment verified for order {order_id}")

                return redirect("bulk_orders:order_success", order_id=order.id)

        messages.error(request, "Payment verification failed")
        return redirect("bulk_orders:order_landing", link_code=order.bulk_order.id)

    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        messages.error(request, "An error occurred verifying your payment")
        return redirect("bulk_orders:order_landing", link_code=order.bulk_order.id)


@csrf_exempt
def payment_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        paystack_signature = request.headers.get("x-paystack-signature")
        if not paystack_signature:
            logger.error("No Paystack signature in webhook request")
            return HttpResponse(status=400)

        secret_key, _ = get_paystack_keys()

        computed_hash = hmac.new(
            bytes(secret_key, "utf-8"), request.body, hashlib.sha512
        ).hexdigest()

        if computed_hash != paystack_signature:
            logger.error("Invalid Paystack signature")
            return HttpResponse(status=400)

        with database_ops_optimizer():
            payload = json.loads(request.body)

            if payload["event"] == "charge.success":
                reference = payload["data"]["reference"]
                order_id = reference.replace("ORDER-", "")

                try:
                    with transaction.atomic():
                        order = OrderEntry.objects.select_for_update().get(id=order_id)

                        if not order.paid:
                            order.paid = True
                            order.payment_reference = reference
                            order.save()

                            # Return 200 immediately after saving payment status
                            response = HttpResponse(status=200)

                            try:
                                generate_receipt(order)
                            except Exception as e:
                                logger.error(
                                    f"Error generating receipt for order {order_id}: {str(e)}"
                                )

                            return response

                except OrderEntry.DoesNotExist:
                    logger.error(f"Order not found: {order_id}")
                except Exception as save_error:
                    logger.error(f"Error saving order {order_id}: {str(save_error)}")
                    return HttpResponse(status=500)

        return HttpResponse(status=200)

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook payload: {str(e)}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return HttpResponse(status=500)


def order_success(request, order_id):
    """Handle successful orders with optimized queries."""
    order = get_object_or_404(
        OrderEntry.objects.select_related("bulk_order", "coupon_used"), id=order_id
    )

    if not order.coupon_used and not order.paid:
        reference = request.GET.get("reference")
        if reference:
            secret_key, _ = get_paystack_keys()

            response = requests.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers={"Authorization": f"Bearer {secret_key}"},
            )

            if response.status_code == 200:
                response_data = response.json()
                if response_data["data"]["status"] == "success":
                    with transaction.atomic():
                        order.paid = True
                        order.payment_reference = reference
                        order.save()

                        try:
                            generate_receipt(order)
                        except Exception as e:
                            logger.error(f"Error generating receipt: {str(e)}")

    # Check if order is valid (either paid or used coupon)
    if not order.paid and not order.coupon_used:
        messages.error(request, "Invalid order access.")
        return redirect("bulk_orders:order_landing", link_code=order.bulk_order.id)

    return render(
        request,
        "bulk_orders/order_success.html",
        {"order": order, "bulk_order": order.bulk_order},
    )


@staff_member_required
def download_pdf(request, link_id):
    """Generate PDF with optimized database operations."""
    bulk_order = get_object_or_404(
        BulkOrderLink.objects.prefetch_related(
            Prefetch(
                "orders",
                queryset=OrderEntry.objects.select_related("coupon_used")
                .filter(Q(paid=True) | Q(coupon_used__isnull=False))
                .order_by("size", "full_name"),
            )
        ),
        id=link_id,
    )

    try:
        # Get orders
        orders = bulk_order.orders.all()

        # Generate size summary
        size_summary = (
            orders.values("size").annotate(count=Count("size")).order_by("size")
        )

        # Prepare context
        context = {
            "bulk_order": bulk_order,
            "size_summary": size_summary,
            "orders": orders,
            "total_orders": orders.count(),
        }

        # Render template to HTML
        html_string = render_to_string("bulk_orders/admin/pdf_template.html", context)

        # Generate PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        pdf = html.write_pdf()

        # Create response
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="order_summary_{bulk_order.id}.pdf"'
        )
        return response

    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        messages.error(request, "Error generating PDF")
        return redirect("admin:bulk_orders_bulkorderlink_changelist")


@staff_member_required
def download_word(request, link_id):
    """Generate Word document with optimized database operations."""
    bulk_order = get_object_or_404(
        BulkOrderLink.objects.prefetch_related(
            Prefetch(
                "orders",
                queryset=OrderEntry.objects.select_related("coupon_used")
                .filter(Q(paid=True) | Q(coupon_used__isnull=False))
                .order_by("size", "full_name"),
            )
        ),
        id=link_id,
    )

    try:
        # Create document
        doc = Document()
        doc.add_heading(f"Order Summary - {bulk_order.organization_name}", 0)

        # Process orders in batches
        orders = bulk_order.orders.all()
        paginator = Paginator(orders, 1000)  # Process 1000 orders at a time

        # Add size summary section
        doc.add_heading("Summary by Size", level=1)
        with database_ops_optimizer():
            size_summary = (
                orders.values("size")
                .annotate(
                    total=Count("id"),
                    paid=Count("id", filter=Q(paid=True)),
                    coupon=Count("id", filter=Q(coupon_used__isnull=False)),
                )
                .order_by("size")
            )

            # Summary table
            table = doc.add_table(rows=1, cols=4)
            table.style = "Table Grid"
            header_cells = table.rows[0].cells
            header_cells[0].text = "Size"
            header_cells[1].text = "Total"
            header_cells[2].text = "Paid"
            header_cells[3].text = "Coupon"

            for size_info in size_summary:
                row_cells = table.add_row().cells
                row_cells[0].text = size_info["size"]
                row_cells[1].text = str(size_info["total"])
                row_cells[2].text = str(size_info["paid"])
                row_cells[3].text = str(size_info["coupon"])

        doc.add_paragraph()

        # Process orders by size
        for page_num in paginator.page_range:
            page = paginator.page(page_num)

            # Group orders by size for this page
            size_groups = {}
            for order in page.object_list:
                if order.size not in size_groups:
                    size_groups[order.size] = []
                size_groups[order.size].append(order)

            # Add orders for each size group
            for size, size_orders in sorted(size_groups.items()):
                doc.add_heading(f"Size: {size}", level=2)

                # Orders table
                table = doc.add_table(rows=1, cols=4)
                table.style = "Table Grid"
                header_cells = table.rows[0].cells
                header_cells[0].text = "S/N"
                header_cells[1].text = "Name"
                header_cells[2].text = (
                    "Custom Name" if bulk_order.custom_branding_enabled else ""
                )
                header_cells[3].text = "Status"

                for idx, order in enumerate(size_orders, 1):
                    row_cells = table.add_row().cells
                    row_cells[0].text = str(idx)
                    row_cells[1].text = order.full_name
                    row_cells[2].text = order.custom_name or ""
                    row_cells[3].text = "Coupon" if order.coupon_used else "Paid"

                doc.add_paragraph()

        # Save document
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="order_summary_{bulk_order.id}.docx"'
        )
        return response

    except Exception as e:
        logger.error(f"Error generating Word document: {str(e)}")
        messages.error(request, "Error generating Word document")
        return redirect("admin:bulk_orders_bulkorderlink_changelist")


@staff_member_required
def generate_size_summary_view(request, link_id):
    """Generate Excel summary with optimized database operations."""
    bulk_order = get_object_or_404(
        BulkOrderLink.objects.prefetch_related(
            Prefetch(
                "orders",
                queryset=OrderEntry.objects.select_related("coupon_used")
                .filter(Q(paid=True) | Q(coupon_used__isnull=False))
                .order_by("size", "full_name"),
            )
        ),
        id=link_id,
    )

    try:
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"constant_memory": True})

        # Add formats
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#f0f0f0", "border": 1, "align": "center"}
        )

        cell_format = workbook.add_format({"border": 1, "align": "center"})

        # Create worksheet
        worksheet = workbook.add_worksheet(bulk_order.organization_name[:31])

        # Headers
        headers = ["S/N", "Size", "Name", "Custom Name", "Status"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Process orders in chunks
        row = 1
        chunk_size = 1000
        orders = bulk_order.orders.all()

        for i in range(0, orders.count(), chunk_size):
            order_chunk = orders[i : i + chunk_size]

            for order in order_chunk:
                worksheet.write(row, 0, row, cell_format)
                worksheet.write(row, 1, order.size, cell_format)
                worksheet.write(row, 2, order.full_name, cell_format)
                worksheet.write(row, 3, order.custom_name or "", cell_format)
                worksheet.write(
                    row, 4, "Coupon" if order.coupon_used else "Paid", cell_format
                )
                row += 1

        # Size Summary with optimized query
        summary_row = row + 2
        worksheet.merge_range(
            summary_row, 0, summary_row, 4, "Size Summary", header_format
        )

        summary_headers = ["Size", "Total", "Paid", "Coupon"]
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
            worksheet.write(summary_row, 0, size_data["size"], cell_format)
            worksheet.write(summary_row, 1, size_data["total"], cell_format)
            worksheet.write(summary_row, 2, size_data["paid"], cell_format)
            worksheet.write(summary_row, 3, size_data["coupon"], cell_format)

        # Adjust column widths
        worksheet.set_column(0, 0, 5)  # S/N
        worksheet.set_column(1, 1, 10)  # Size
        worksheet.set_column(2, 2, 30)  # Name
        worksheet.set_column(3, 3, 30)  # Custom Name
        worksheet.set_column(4, 4, 15)  # Status

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = f'size_summary_{bulk_order.organization_name}_{timezone.now().strftime("%Y%m%d")}.xlsx'
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        logger.error(f"Error generating Excel summary: {str(e)}")
        messages.error(request, "Error generating Excel summary")
        return redirect("admin:bulk_orders_bulkorderlink_changelist")
