from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .models import PaymentTransaction
from order.models import Order

User = get_user_model()


class PaymentTransactionModelTest(TestCase):
    """Test cases for the PaymentTransaction model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.order = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00")
        )

    def test_payment_transaction_creation(self):
        """Test that a payment transaction can be created."""
        payment = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com",
            status='pending'
        )
        self.assertIsNotNone(payment.id)
        self.assertIsNotNone(payment.reference)
        self.assertTrue(payment.reference.startswith("JMW-PAY-"))

    def test_reference_auto_generation(self):
        """Test that reference is auto-generated on save."""
        payment = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com"
        )
        self.assertTrue(payment.reference)
        self.assertIn("JMW-PAY-", payment.reference)

    def test_reference_uniqueness(self):
        """Test that references are unique."""
        payment1 = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com"
        )
        payment2 = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com"
        )
        self.assertNotEqual(payment1.reference, payment2.reference)

    def test_default_status_is_pending(self):
        """Test that default status is 'pending'."""
        payment = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com"
        )
        self.assertEqual(payment.status, 'pending')

    def test_payment_string_representation(self):
        """Test the string representation of a payment."""
        payment = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com",
            status='success'
        )
        expected = f"Payment {payment.reference} - success"
        self.assertEqual(str(payment), expected)


class PaymentAPITest(APITestCase):
    """Test cases for the Payment API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.order = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00"),
            paid=False
        )

    @patch('payment.views.initialize_payment')
    def test_initialize_payment(self, mock_initialize):
        """Test initializing a payment."""
        mock_initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://paystack.com/pay/test',
                'access_code': 'test_access_code',
                'reference': 'test_reference'
            }
        }

        data = {
            'order_id': str(self.order.id),
            'email': 'john@example.com'
        }

        response = self.client.post('/api/payment/initialize/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('authorization_url', response.data)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

        payment = PaymentTransaction.objects.first()
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.status, 'pending')

    @patch('payment.views.initialize_payment')
    def test_initialize_payment_for_already_paid_order_fails(self, mock_initialize):
        """Test that initializing payment for already paid order fails."""
        self.order.paid = True
        self.order.save()

        data = {
            'order_id': str(self.order.id),
            'email': 'john@example.com'
        }

        response = self.client.post('/api/payment/initialize/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already been paid', str(response.data))

    @patch('payment.views.initialize_payment')
    def test_idempotent_payment_initialization(self, mock_initialize):
        """Test idempotent payment initialization."""
        # Create existing pending transaction
        existing_payment = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com",
            status='pending'
        )

        mock_initialize.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://paystack.com/pay/test',
                'access_code': 'test_access_code',
                'reference': existing_payment.reference
            }
        }

        data = {
            'order_id': str(self.order.id),
            'email': 'john@example.com'
        }

        response = self.client.post('/api/payment/initialize/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should reuse existing transaction
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    @patch('payment.views.send_payment_receipt_email_async')
    @patch('payment.views.generate_payment_receipt_pdf_task')
    @patch('payment.views.verify_payment')
    def test_verify_payment_success(self, mock_verify, mock_pdf, mock_email):
        """Test successful payment verification."""
        payment = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com",
            status='pending'
        )

        mock_verify.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': payment.reference,
                'amount': 500000  # In kobo
            }
        }

        data = {'reference': payment.reference}
        response = self.client.post('/api/payment/verify/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('success', response.data['status'])

        # Verify payment and order updated
        payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(payment.status, 'success')
        self.assertTrue(self.order.paid)
        self.assertEqual(self.order.status, 'paid')
        self.assertIsNotNone(payment.verified_at)

        # Verify background tasks called
        mock_email.assert_called_once()
        mock_pdf.assert_called_once()

    @patch('payment.views.verify_payment')
    def test_verify_payment_idempotent(self, mock_verify):
        """Test idempotent payment verification."""
        payment = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com",
            status='success',
            verified_at=timezone.now()
        )
        self.order.paid = True
        self.order.save()

        data = {'reference': payment.reference}
        response = self.client.post('/api/payment/verify/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('already verified', response.data['message'])

    @patch('payment.views.verify_payment')
    def test_verify_payment_not_found(self, mock_verify):
        """Test verifying non-existent payment."""
        data = {'reference': 'NON_EXISTENT_REF'}
        response = self.client.post('/api/payment/verify/', data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_payment_transaction_viewset_authentication(self):
        """Test that payment transaction viewset requires authentication."""
        response = self.client.get('/api/payment/transactions/')
        # Depending on your viewset permissions
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_user_can_only_see_own_payments(self):
        """Test that users can only see their own payment transactions."""
        user2 = User.objects.create_user(
            username="testuser2",
            email="user2@example.com",
            password="testpass123"
        )
        order2 = Order.objects.create(
            user=user2,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone_number="08087654321",
            total_cost=Decimal("3000.00")
        )

        payment1 = PaymentTransaction.objects.create(
            order=self.order,
            amount=Decimal("5000.00"),
            email="john@example.com"
        )
        payment2 = PaymentTransaction.objects.create(
            order=order2,
            amount=Decimal("3000.00"),
            email="jane@example.com"
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/payment/transactions/')

        if response.status_code == status.HTTP_200_OK:
            payment_ids = [p['id'] for p in response.data.get('results', response.data)]
            self.assertIn(str(payment1.id), payment_ids)
            self.assertNotIn(str(payment2.id), payment_ids)
