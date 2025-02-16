from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import PaymentTransaction
from .utils import initialize_payment, verify_payment, get_paystack_keys
from order.utils import generate_receipt_pdf, send_receipt_email
import json
from order.models import BaseOrder
import uuid
import logging

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class InitiatePaymentView(View):
    def get(self, request):
        return self.handle_payment(request)

    def post(self, request):
        return self.handle_payment(request)

    def handle_payment(self, request):
        try:
            logger = logging.getLogger(__name__)

            # Get the orders from the session
            order_ids = request.session.get("pending_orders", [])
            logger.info(f"Processing payment for orders: {order_ids}")

            # Convert string UUIDs back to UUIDs for the query
            orders = BaseOrder.objects.filter(
                id__in=[uuid.UUID(id_str) for id_str in order_ids]
            )

            if not orders:
                messages.error(request, "No orders found to process payment.")
                return redirect("order:checkout")

            # Create payment transaction
            first_order = orders.first()
            total_amount = sum(order.total_cost for order in orders)

            payment = PaymentTransaction.objects.create(
                amount=total_amount, email=first_order.email
            )
            payment.orders.set(orders)

            logger.info(
                f"Created payment transaction: {payment.reference} for amount: {total_amount}"
            )

            # Get callback URL
            callback_url = request.build_absolute_uri(reverse("payment:verify_payment"))

            # Initialize payment with Paystack
            response = initialize_payment(
                amount=payment.amount,
                email=payment.email,
                reference=payment.reference,
                callback_url=callback_url,
                metadata={
                    "orders": [str(order.id) for order in orders],
                    "customer_name": f"{first_order.first_name} {first_order.last_name}",
                },
            )

            if response is None:
                messages.error(
                    request, "Could not initialize payment. Please try again."
                )
                return redirect("order:checkout")

            if response.get("status"):
                authorization_url = response["data"]["authorization_url"]
                logger.info(
                    f"Payment initialized successfully. Redirecting to: {authorization_url}"
                )

                # Clear session
                request.session.pop("pending_orders", None)

                # Redirect to Paystack payment page
                return redirect(authorization_url)

            logger.error(
                f"Payment initialization failed: {response.get('message', 'Unknown error')}"
            )
            messages.error(request, "Could not initialize payment. Please try again.")
            return redirect("order:checkout")

        except Exception as e:
            logger.exception("Error processing payment")
            messages.error(request, "An error occurred while processing payment.")
            return redirect("order:checkout")


@login_required
def verify_payment_view(request):
    reference = request.GET.get("reference")
    if not reference:
        messages.error(request, "No reference provided")
        return redirect("order:checkout")

    payment = get_object_or_404(PaymentTransaction, reference=reference)
    response = verify_payment(reference)

    if response.get("status") and response["data"]["status"] == "success":
        payment.status = "success"
        payment.save()

        for order in payment.orders.all():
            order.paid = True
            order.save()

        return redirect("payment:success")

    payment.status = "failed"
    payment.save()
    return redirect("payment:failed")


@csrf_exempt
def payment_webhook(request):
    payload = json.loads(request.body)
    secret_key, _ = get_paystack_keys()

    signature = request.headers.get("x-paystack-signature")
    if signature:
        pass

    if payload["event"] == "charge.success":
        try:
            payment = PaymentTransaction.objects.get(
                reference=payload["data"]["reference"]
            )
            if payment.status != "success":
                payment.status = "success"
                payment.save()

                for order in payment.orders.all():
                    order.paid = True
                    order.save()

                try:
                    pdf = generate_receipt_pdf(payment.orders.all(), payment)
                    send_receipt_email(payment.email, pdf, payment.reference)
                    logger.info(
                        f"Receipt sent successfully for payment {payment.reference}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error generating/sending receipt for payment {payment.reference}: {str(e)}",
                        exc_info=True,
                    )

        except PaymentTransaction.DoesNotExist:
            logger.error(
                f"Payment not found for reference: {payload['data']['reference']}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in webhook: {str(e)}", exc_info=True)

    return HttpResponse(status=200)


def payment_success(request):
    return render(request, "payment/success.html")


def payment_failed(request):
    return render(request, "payment/failed.html")
