# bulk_orders/tests/test_views.py
"""
Comprehensive test suite for bulk_orders views.
Tests cover ViewSets, permissions, actions, webhooks, and all edge cases.
This is the "big iroko" - most complex test suite in the app.
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock, Mock
import json

from bulk_orders.models import BulkOrderLink, CouponCode, OrderEntry
from bulk_orders.views import bulk_order_payment_webhook

User = get_user_model()


class BulkOrderLinkViewSetTest(APITestCase):
    """Test suite for BulkOrderLinkViewSet"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create users
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="userpass123"
        )
        
        # Create bulk orders
        self.bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.admin_user
        )
        
        self.expired_bulk_order = BulkOrderLink.objects.create(
            organization_name="Expired Org",
            price_per_item=Decimal("4000.00"),
            payment_deadline=timezone.now() - timedelta(days=1),
            created_by=self.admin_user
        )

    def test_list_bulk_orders_unauthenticated(self):
        """Test that unauthenticated users see nothing"""
        url = reverse('bulk_orders:bulk-link-list')
        response = self.client.get(url)
        
        # Should return empty list (permission allows read but queryset filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_list_bulk_orders_regular_user(self):
        """Test that regular user sees only their bulk orders"""
        self.client.force_authenticate(user=self.regular_user)
        
        # Create bulk order for regular user
        user_bulk_order = BulkOrderLink.objects.create(
            organization_name="User Org",
            price_per_item=Decimal("3000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.regular_user
        )
        
        url = reverse('bulk_orders:bulk-link-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(user_bulk_order.id))

    def test_list_bulk_orders_admin(self):
        """Test that admin sees all bulk orders"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('bulk_orders:bulk-link-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see at least 2 (test org + expired org)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_retrieve_bulk_order_by_slug(self):
        """Test retrieving bulk order by slug"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('bulk_orders:bulk-link-detail', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['organization_name'], "TEST ORG")
        self.assertEqual(response.data['slug'], self.bulk_order.slug)

    def test_create_bulk_order(self):
        """Test creating bulk order"""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('bulk_orders:bulk-link-list')
        data = {
            'organization_name': 'New Organization',
            'price_per_item': '6000.00',
            'custom_branding_enabled': True,
            'payment_deadline': (timezone.now() + timedelta(days=45)).isoformat()
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['organization_name'], "NEW ORGANIZATION")
        
        # Verify created_by is set to requesting user
        bulk_order = BulkOrderLink.objects.get(id=response.data['id'])
        self.assertEqual(bulk_order.created_by, self.regular_user)

    def test_update_bulk_order(self):
        """Test updating bulk order"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('bulk_orders:bulk-link-detail', kwargs={'slug': self.bulk_order.slug})
        data = {
            'organization_name': 'Updated Org',
            'price_per_item': '7000.00',
            'custom_branding_enabled': False,
            'payment_deadline': (timezone.now() + timedelta(days=60)).isoformat()
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['organization_name'], "UPDATED ORG")

    def test_delete_bulk_order(self):
        """Test deleting bulk order"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('bulk_orders:bulk-link-detail', kwargs={'slug': self.bulk_order.slug})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BulkOrderLink.objects.filter(id=self.bulk_order.id).exists())

    # ========== ACTION TESTS ==========

    def test_generate_coupons_action_requires_admin(self):
        """Test that generate_coupons requires admin permission"""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('bulk_orders:bulk-link-generate-coupons', kwargs={'slug': self.bulk_order.slug})
        response = self.client.post(url, {'count': 10})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_generate_coupons_action_success(self):
        """Test generating coupons successfully"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('bulk_orders:bulk-link-generate-coupons', kwargs={'slug': self.bulk_order.slug})
        response = self.client.post(url, {'count': 25})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 25)
        self.assertIn('sample_codes', response.data)
        
        # Verify coupons were created
        self.assertEqual(self.bulk_order.coupons.count(), 25)

    def test_generate_coupons_already_has_coupons(self):
        """Test that generating coupons fails if already exists"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Create one coupon first
        CouponCode.objects.create(bulk_order=self.bulk_order, code="EXISTING")
        
        url = reverse('bulk_orders:bulk-link-generate-coupons', kwargs={'slug': self.bulk_order.slug})
        response = self.client.post(url, {'count': 10})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already has', response.data['error'])

    @patch('bulk_orders.views.render')
    def test_paid_orders_html_view(self, mock_render):
        """Test paid_orders action returns HTML view"""
        # Create some paid orders
        OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="paid1@example.com",
            full_name="Paid User 1",
            size="L",
            paid=True
        )
        
        mock_render.return_value = Mock(status_code=200)
        
        url = reverse('bulk_orders:bulk-link-paid-orders', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url)
        
        # Should call render (HTML template)
        self.assertTrue(mock_render.called)

    @patch('bulk_orders.views.generate_bulk_order_pdf')
    def test_paid_orders_pdf_download(self, mock_generate_pdf):
        """Test paid_orders with download=pdf parameter"""
        self.client.force_authenticate(user=self.admin_user)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_generate_pdf.return_value = mock_response
        
        url = reverse('bulk_orders:bulk-link-paid-orders', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url, {'download': 'pdf'})
        
        # Should call PDF generation
        self.assertTrue(mock_generate_pdf.called)

    def test_analytics_action_requires_admin(self):
        """Test that analytics requires admin permission"""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('bulk_orders:bulk-link-analytics', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_analytics_action_success(self):
        """Test analytics returns correct statistics"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Create some orders
        OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="test1@example.com",
            full_name="Test 1",
            size="L",
            paid=True
        )
        OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="test2@example.com",
            full_name="Test 2",
            size="M",
            paid=False
        )
        
        # Create coupons
        CouponCode.objects.create(bulk_order=self.bulk_order, code="COUPON1", is_used=True)
        CouponCode.objects.create(bulk_order=self.bulk_order, code="COUPON2", is_used=False)
        
        url = reverse('bulk_orders:bulk-link-analytics', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['overview']['total_orders'], 2)
        self.assertEqual(response.data['overview']['paid_orders'], 1)
        self.assertEqual(response.data['coupons']['total'], 2)
        self.assertEqual(response.data['coupons']['used'], 1)

    @patch('bulk_orders.views.generate_bulk_order_pdf')
    def test_download_pdf_action(self, mock_generate_pdf):
        """Test download_pdf action"""
        self.client.force_authenticate(user=self.admin_user)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_generate_pdf.return_value = mock_response
        
        url = reverse('bulk_orders:bulk-link-download-pdf', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url)
        
        self.assertTrue(mock_generate_pdf.called)

    @patch('bulk_orders.views.generate_bulk_order_word')
    def test_download_word_action(self, mock_generate_word):
        """Test download_word action"""
        self.client.force_authenticate(user=self.admin_user)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_generate_word.return_value = mock_response
        
        url = reverse('bulk_orders:bulk-link-download-word', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url)
        
        self.assertTrue(mock_generate_word.called)

    @patch('bulk_orders.views.generate_bulk_order_excel')
    def test_generate_size_summary_action(self, mock_generate_excel):
        """Test generate_size_summary (Excel) action"""
        self.client.force_authenticate(user=self.admin_user)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_generate_excel.return_value = mock_response
        
        url = reverse('bulk_orders:bulk-link-generate-size-summary', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url)
        
        self.assertTrue(mock_generate_excel.called)

    def test_stats_action_public(self):
        """Test stats action is publicly accessible"""
        # No authentication
        url = reverse('bulk_orders:bulk-link-stats', kwargs={'slug': self.bulk_order.slug})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('organization', response.data)
        self.assertIn('total_orders', response.data)
        self.assertIn('is_expired', response.data)

    @patch('jmw.background_utils.send_order_confirmation_email')
    def test_submit_order_action(self, mock_email):
        """Test submit_order action (nested order creation)"""
        # No authentication required (AllowAny)
        url = reverse('bulk_orders:bulk-link-submit-order', kwargs={'slug': self.bulk_order.slug})
        data = {
            'email': 'neworder@example.com',
            'full_name': 'New Order',
            'size': 'XL'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'neworder@example.com')
        
        # Verify order was created
        order = OrderEntry.objects.get(id=response.data['id'])
        self.assertEqual(order.bulk_order, self.bulk_order)
        
        # Verify email was sent
        mock_email.assert_called_once()

    @patch('jmw.background_utils.send_order_confirmation_email')
    def test_submit_order_expired_bulk_order(self, mock_email):
        """Test submit_order rejects expired bulk orders"""
        url = reverse('bulk_orders:bulk-link-submit-order', kwargs={'slug': self.expired_bulk_order.slug})
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'size': 'L'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', str(response.data).lower())


class OrderEntryViewSetTest(APITestCase):
    """Test suite for OrderEntryViewSet"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        self.order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="test@example.com",
            full_name="Test User",
            size="L"
        )

    def test_list_orders_unauthenticated(self):
        """Test that unauthenticated users see nothing"""
        url = reverse('bulk_orders:bulk-order-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_list_orders_authenticated(self):
        """Test that user sees only their orders (by email)"""
        self.client.force_authenticate(user=self.user)
        
        # Create another order with same email
        OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="test@example.com",
            full_name="Another Order",
            size="M"
        )
        
        # Create order with different email
        OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="other@example.com",
            full_name="Other User",
            size="S"
        )
        
        url = reverse('bulk_orders:bulk-order-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see orders with test@example.com
        self.assertEqual(len(response.data['results']), 2)

    def test_retrieve_order(self):
        """Test retrieving specific order"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('bulk_orders:bulk-order-detail', kwargs={'pk': self.order.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], "test@example.com")

    @patch('bulk_orders.views.initialize_payment')
    def test_initialize_payment_action(self, mock_initialize_payment):
        """Test initialize_payment action"""
        self.client.force_authenticate(user=self.user)
        
        mock_initialize_payment.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://paystack.com/pay/abc123',
                'access_code': 'abc123',
            }
        }
        
        url = reverse('bulk_orders:bulk-order-initialize-payment', kwargs={'pk': self.order.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('authorization_url', response.data)
        self.assertIn('reference', response.data)
        
        # Verify reference format
        reference = response.data['reference']
        self.assertTrue(reference.startswith(f"ORDER-{self.bulk_order.id}-{self.order.id}"))

    def test_initialize_payment_already_paid(self):
        """Test initialize_payment rejects already paid orders"""
        self.client.force_authenticate(user=self.user)
        
        self.order.paid = True
        self.order.save()
        
        url = reverse('bulk_orders:bulk-order-initialize-payment', kwargs={'pk': self.order.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already been paid', response.data['error'])

    @patch('bulk_orders.views.initialize_payment')
    def test_initialize_payment_paystack_failure(self, mock_initialize_payment):
        """Test initialize_payment handles Paystack failure"""
        self.client.force_authenticate(user=self.user)
        
        mock_initialize_payment.return_value = None  # Paystack failed
        
        url = reverse('bulk_orders:bulk-order-initialize-payment', kwargs={'pk': self.order.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('initialization failed', response.data['error'])


class CouponCodeViewSetTest(APITestCase):
    """Test suite for CouponCodeViewSet"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="userpass123"
        )
        
        self.bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.admin_user
        )
        
        self.coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="TESTCOUPON"
        )

    def test_list_coupons_requires_admin(self):
        """Test that listing coupons requires admin permission"""
        self.client.force_authenticate(user=self.regular_user)
        
        url = reverse('bulk_orders:bulk-coupon-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_coupons_admin(self):
        """Test that admin can list coupons"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('bulk_orders:bulk-coupon-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_list_coupons_filtered_by_bulk_order(self):
        """Test filtering coupons by bulk_order_slug"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Create another bulk order with coupons
        other_bulk_order = BulkOrderLink.objects.create(
            organization_name="Other Org",
            price_per_item=Decimal("3000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.admin_user
        )
        CouponCode.objects.create(bulk_order=other_bulk_order, code="OTHER1")
        CouponCode.objects.create(bulk_order=other_bulk_order, code="OTHER2")
        
        url = reverse('bulk_orders:bulk-coupon-list')
        response = self.client.get(url, {'bulk_order_slug': self.bulk_order.slug})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see coupons from self.bulk_order
        self.assertEqual(len(response.data['results']), 1)

    def test_validate_coupon_action_unused(self):
        """Test validate_coupon action with unused coupon"""
        self.client.force_authenticate(user=self.admin_user)
        
        url = reverse('bulk_orders:bulk-coupon-validate-coupon', kwargs={'pk': self.coupon.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['code'], "TESTCOUPON")

    def test_validate_coupon_action_used(self):
        """Test validate_coupon action with used coupon"""
        self.client.force_authenticate(user=self.admin_user)
        
        self.coupon.is_used = True
        self.coupon.save()
        
        url = reverse('bulk_orders:bulk-coupon-validate-coupon', kwargs={'pk': self.coupon.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['valid'])
        self.assertIn('already been used', response.data['message'])


class PaymentWebhookTest(TransactionTestCase):
    """Test suite for bulk_order_payment_webhook"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        self.order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="test@example.com",
            full_name="Test User",
            size="L",
            paid=False
        )
        
        self.reference = f"ORDER-{self.bulk_order.id}-{self.order.id}"

    @patch('bulk_orders.views.verify_payment')
    @patch('bulk_orders.views.send_payment_receipt_email')
    @patch('bulk_orders.views.generate_payment_receipt_pdf_task')
    def test_webhook_success(self, mock_pdf_task, mock_email, mock_verify):
        """Test successful webhook processing"""
        # Mock Paystack verification
        mock_verify.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'amount': 500000,  # 5000.00 in kobo
            }
        }
        
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': self.reference,
                'amount': 500000,
                'status': 'success'
            }
        }
        
        url = reverse('bulk_orders:payment-webhook')
        response = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify order was marked as paid
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)
        
        # Verify email and PDF generation were triggered
        mock_email.assert_called_once_with(self.order)
        mock_pdf_task.assert_called_once()

    @patch('bulk_orders.views.verify_payment')
    def test_webhook_invalid_event(self, mock_verify):
        """Test webhook ignores non-charge.success events"""
        payload = {
            'event': 'charge.failed',
            'data': {
                'reference': self.reference,
            }
        }
        
        url = reverse('bulk_orders:payment-webhook')
        response = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ignored')

    def test_webhook_invalid_reference_format(self):
        """Test webhook rejects invalid reference format"""
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': 'INVALID-REF-123',
            }
        }
        
        url = reverse('bulk_orders:payment-webhook')
        response = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')

    @patch('bulk_orders.views.verify_payment')
    def test_webhook_verification_failure(self, mock_verify):
        """Test webhook handles verification failure"""
        mock_verify.return_value = {
            'status': False,
            'message': 'Verification failed'
        }
        
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': self.reference,
            }
        }
        
        url = reverse('bulk_orders:payment-webhook')
        response = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)

    @patch('bulk_orders.views.verify_payment')
    def test_webhook_order_not_found(self, mock_verify):
        """Test webhook handles missing order"""
        mock_verify.return_value = {
            'status': True,
            'data': {'status': 'success'}
        }
        
        # Use non-existent order ID
        fake_reference = f"ORDER-{self.bulk_order.id}-00000000-0000-0000-0000-000000000000"
        
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': fake_reference,
            }
        }
        
        url = reverse('bulk_orders:payment-webhook')
        response = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)

    @patch('bulk_orders.views.verify_payment')
    @patch('bulk_orders.views.send_payment_receipt_email')
    def test_webhook_idempotency(self, mock_email, mock_verify):
        """Test webhook is idempotent (doesn't process twice)"""
        mock_verify.return_value = {
            'status': True,
            'data': {'status': 'success'}
        }
        
        # Mark order as already paid
        self.order.paid = True
        self.order.save()
        
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': self.reference,
            }
        }
        
        url = reverse('bulk_orders:payment-webhook')
        response = self.client.post(
            url,
            json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['message'], 'Already processed')
        
        # Email should NOT be sent again
        mock_email.assert_not_called()

    def test_webhook_invalid_json(self):
        """Test webhook handles invalid JSON"""
        url = reverse('bulk_orders:payment-webhook')
        response = self.client.post(
            url,
            'invalid json{',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)

    def test_webhook_wrong_http_method(self):
        """Test webhook only accepts POST"""
        url = reverse('bulk_orders:payment-webhook')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 405)


class PermissionTest(APITestCase):
    """Test permission enforcement across views"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="adminpass",
            is_staff=True
        )
        self.user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="userpass"
        )
        
        self.bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.admin
        )

    def test_admin_only_actions(self):
        """Test actions that require admin permission"""
        admin_only_actions = [
            ('bulk_orders:bulk-link-generate-coupons', {'slug': self.bulk_order.slug}),
            ('bulk_orders:bulk-link-analytics', {'slug': self.bulk_order.slug}),
            ('bulk_orders:bulk-link-download-pdf', {'slug': self.bulk_order.slug}),
            ('bulk_orders:bulk-link-download-word', {'slug': self.bulk_order.slug}),
            ('bulk_orders:bulk-link-generate-size-summary', {'slug': self.bulk_order.slug}),
        ]
        
        for url_name, kwargs in admin_only_actions:
            # Test with regular user (should be forbidden)
            self.client.force_authenticate(user=self.user)
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url) if 'download' in url_name or 'analytics' in url_name else self.client.post(url)
            
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"{url_name} should require admin permission"
            )
            
            # Test with admin (should succeed or at least not be 403)
            self.client.force_authenticate(user=self.admin)
            response = self.client.get(url) if 'download' in url_name or 'analytics' in url_name else self.client.post(url, {'count': 10})
            
            self.assertNotEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"{url_name} should allow admin access"
            )

    def test_public_actions(self):
        """Test actions that allow any access"""
        public_actions = [
            ('bulk_orders:bulk-link-stats', {'slug': self.bulk_order.slug}),
            ('bulk_orders:bulk-link-paid-orders', {'slug': self.bulk_order.slug}),
            ('bulk_orders:bulk-link-submit-order', {'slug': self.bulk_order.slug}),
        ]
        
        for url_name, kwargs in public_actions:
            # Test without authentication
            self.client.force_authenticate(user=None)
            url = reverse(url_name, kwargs=kwargs)
            
            if 'submit-order' in url_name:
                response = self.client.post(url, {
                    'email': 'test@example.com',
                    'full_name': 'Test',
                    'size': 'L'
                })
            else:
                response = self.client.get(url)
            
            self.assertNotEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"{url_name} should be publicly accessible"
            )


if __name__ == "__main__":
    import unittest
    unittest.main()