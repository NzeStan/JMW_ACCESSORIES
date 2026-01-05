from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.shortcuts import get_object_or_404
from django.conf import settings
from .serializers import PaymentInitializeSerializer, PaymentVerifySerializer, PaymentTransactionSerializer
from .models import PaymentTransaction
from .utils import initialize_payment, verify_payment
from order.models import Order
from order.utils import generate_receipt_pdf, send_receipt_email
import uuid

class InitializePaymentView(APIView):
    def post(self, request):
        serializer = PaymentInitializeSerializer(data=request.data)
        if serializer.is_valid():
            order_id = serializer.validated_data['order_id']
            email = serializer.validated_data['email']
            
            order = get_object_or_404(Order, id=order_id)
            
            # Generate reference
            reference = f"JMW-{uuid.uuid4().hex[:8].upper()}"
            
            # Create Transaction Record
            transaction = PaymentTransaction.objects.create(
                reference=reference,
                amount=order.total_cost,
                email=email,
                status='pending'
            )
            transaction.orders.add(order)
            
            # Initialize Paystack
            callback_url = "http://localhost:3000/payment/callback" # Update with frontend URL
            res = initialize_payment(order.total_cost, email, reference, callback_url)
            
            if res and res.get('status'):
                return Response(res['data'])
            return Response({"error": "Payment initialization failed"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyPaymentView(APIView):
    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        if serializer.is_valid():
            reference = serializer.validated_data['reference']
            res = verify_payment(reference)
            
            if res and res.get('status') and res['data']['status'] == 'success':
                try:
                    transaction = PaymentTransaction.objects.get(reference=reference)
                    transaction.status = 'success'
                    transaction.save()
                    
                    for order in transaction.orders.all():
                        order.paid = True
                        order.status = 'paid'
                        order.save()
                    
                    # Send Receipt Email
                    if settings.USE_CELERY_EMAIL:
                        send_receipt_email_task.delay(transaction.id)
                    else:
                        try:
                            pdf = generate_receipt_pdf(transaction.orders.all(), transaction)
                            send_receipt_email(transaction.email, pdf, transaction.reference)
                        except Exception as e:
                            # Log error (assuming logger is configured or just pass for now)
                            print(f"Error sending email: {e}")

                    return Response({"status": "success", "message": "Payment verified"})
                except PaymentTransaction.DoesNotExist:
                    return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({"error": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentTransaction.objects.all()
    serializer_class = PaymentTransactionSerializer
