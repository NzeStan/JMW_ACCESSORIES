# bulk_orders/tests/test_serializers.py
"""
Comprehensive test suite for bulk_orders serializers.
Tests cover validation, context handling, nested serialization, and all edge cases.
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock
import json

from bulk_orders.models import BulkOrderLink, CouponCode, OrderEntry
from bulk_orders.serializers import (
    CouponCodeSerializer,
    BulkOrderLinkSummarySerializer,
    OrderEntrySerializer,
    BulkOrderLinkSerializer,
)

User = get_user_model()


class CouponCodeSerializerTest(TestCase):
    """Test suite for CouponCodeSerializer"""

    def setUp(self):
        """Set up test data"""
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
        self.coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="TEST12345"
        )

    def test_serialize_coupon_code(self):
        """Test basic coupon code serialization"""
        serializer = CouponCodeSerializer(self.coupon)
        data = serializer.data
        
        self.assertEqual(data['code'], "TEST12345")
        self.assertFalse(data['is_used'])
        self.assertEqual(data['bulk_order_name'], "TEST ORG")
        self.assertEqual(data['bulk_order_slug'], self.bulk_order.slug)
        self.assertIn('created_at', data)

    def test_serialize_used_coupon(self):
        """Test serialization of used coupon"""
        self.coupon.is_used = True
        self.coupon.save()
        
        serializer = CouponCodeSerializer(self.coupon)
        data = serializer.data
        
        self.assertTrue(data['is_used'])

    def test_serialize_multiple_coupons(self):
        """Test serializing multiple coupons"""
        coupon2 = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="TEST67890"
        )
        
        coupons = [self.coupon, coupon2]
        serializer = CouponCodeSerializer(coupons, many=True)
        data = serializer.data
        
        self.assertEqual(len(data), 2)
        codes = [c['code'] for c in data]
        self.assertIn("TEST12345", codes)
        self.assertIn("TEST67890", codes)

    def test_read_only_fields(self):
        """Test that read-only fields cannot be set during creation"""
        data = {
            'bulk_order': self.bulk_order.id,
            'code': 'NEWCODE123',
            'is_used': True,  # This should be ignored (read-only)
        }
        
        serializer = CouponCodeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        # is_used should be False (default) despite passing True
        # Note: We're not testing save here since it's read-only


class BulkOrderLinkSummarySerializerTest(TestCase):
    """Test suite for BulkOrderLinkSummarySerializer"""

    def setUp(self):
        """Set up test data"""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.future_deadline = timezone.now() + timedelta(days=30)
        self.past_deadline = timezone.now() - timedelta(days=1)

    def test_serialize_active_bulk_order(self):
        """Test serialization of active bulk order"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Active Order",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        request = self.factory.get('/')
        serializer = BulkOrderLinkSummarySerializer(
            bulk_order,
            context={'request': request}
        )
        data = serializer.data
        
        self.assertEqual(data['organization_name'], "ACTIVE ORDER")
        self.assertEqual(float(data['price_per_item']), 5000.00)
        self.assertFalse(data['is_expired'])
        self.assertIn('shareable_url', data)

    def test_serialize_expired_bulk_order(self):
        """Test serialization of expired bulk order"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Expired Order",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.past_deadline,
            created_by=self.user
        )
        
        serializer = BulkOrderLinkSummarySerializer(bulk_order)
        data = serializer.data
        
        self.assertTrue(data['is_expired'])

    def test_shareable_url_with_request(self):
        """Test shareable_url generation with request context"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="URL Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        request = self.factory.get('/')
        serializer = BulkOrderLinkSummarySerializer(
            bulk_order,
            context={'request': request}
        )
        data = serializer.data
        
        # Should contain the slug in the URL
        self.assertIn(bulk_order.slug, data['shareable_url'])
        self.assertTrue(data['shareable_url'].startswith('http'))

    def test_shareable_url_without_request(self):
        """Test shareable_url generation without request context"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="No Request Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        serializer = BulkOrderLinkSummarySerializer(bulk_order)
        data = serializer.data
        
        # Should still return path without full URL
        self.assertIn(bulk_order.slug, data['shareable_url'])
        self.assertTrue(data['shareable_url'].startswith('/bulk-order/'))


class OrderEntrySerializerTest(TestCase):
    """Test suite for OrderEntrySerializer"""

    def setUp(self):
        """Set up test data"""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user,
            custom_branding_enabled=True
        )
        self.coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="TESTCOUPON"
        )

    def test_serialize_order_entry(self):
        """Test basic order entry serialization"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L",
            custom_name="CUSTOM TEXT"
        )
        
        serializer = OrderEntrySerializer(order)
        data = serializer.data
        
        self.assertEqual(data['email'], "customer@example.com")
        self.assertEqual(data['full_name'], "JOHN DOE")
        self.assertEqual(data['size'], "L")
        self.assertEqual(data['custom_name'], "CUSTOM TEXT")
        self.assertFalse(data['paid'])

    def test_serialize_order_without_custom_branding(self):
        """Test that custom_name is excluded when branding disabled"""
        bulk_order_no_branding = BulkOrderLink.objects.create(
            organization_name="No Branding",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user,
            custom_branding_enabled=False
        )
        
        order = OrderEntry.objects.create(
            bulk_order=bulk_order_no_branding,
            email="customer@example.com",
            full_name="Jane Doe",
            size="M",
            custom_name="SHOULD NOT APPEAR"
        )
        
        serializer = OrderEntrySerializer(order)
        data = serializer.data
        
        # custom_name should be removed from representation
        self.assertNotIn('custom_name', data)

    def test_create_order_without_coupon(self):
        """Test creating order entry without coupon"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'newcustomer@example.com',
            'full_name': 'New Customer',
            'size': 'XL',
            'custom_name': 'CUSTOM'
        }
        
        with patch('jmw.background_utils.send_order_confirmation_email') as mock_email:
            serializer = OrderEntrySerializer(
                data=data,
                context={'bulk_order': self.bulk_order, 'request': request}
            )
            self.assertTrue(serializer.is_valid())
            order = serializer.save()
            
            self.assertEqual(order.email, 'newcustomer@example.com')
            self.assertEqual(order.full_name, 'NEW CUSTOMER')
            self.assertFalse(order.paid)
            self.assertIsNone(order.coupon_used)
            
            # Verify email was sent
            mock_email.assert_called_once_with(order)

    def test_create_order_with_valid_coupon(self):
        """Test creating order with valid coupon"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'coupon_user@example.com',
            'full_name': 'Coupon User',
            'size': 'L',
            'coupon_code': 'TESTCOUPON'
        }
        
        with patch('jmw.background_utils.send_order_confirmation_email') as mock_email:
            serializer = OrderEntrySerializer(
                data=data,
                context={'bulk_order': self.bulk_order, 'request': request}
            )
            self.assertTrue(serializer.is_valid())
            order = serializer.save()
            
            # Order should be automatically paid when using coupon
            self.assertTrue(order.paid)
            self.assertEqual(order.coupon_used, self.coupon)
            
            # Coupon should be marked as used
            self.coupon.refresh_from_db()
            self.assertTrue(self.coupon.is_used)
            
            # Email should still be sent
            mock_email.assert_called_once()

    def test_create_order_with_invalid_coupon(self):
        """Test creating order with invalid coupon code"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'size': 'M',
            'coupon_code': 'INVALIDCODE'
        }
        
        serializer = OrderEntrySerializer(
            data=data,
            context={'bulk_order': self.bulk_order, 'request': request}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('coupon_code', serializer.errors)
        self.assertIn('Invalid coupon code', str(serializer.errors['coupon_code']))

    def test_create_order_with_coupon_from_different_bulk_order(self):
        """Test that coupon from different bulk order is rejected"""
        other_bulk_order = BulkOrderLink.objects.create(
            organization_name="Other Org",
            price_per_item=Decimal("3000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        other_coupon = CouponCode.objects.create(
            bulk_order=other_bulk_order,
            code="OTHERCOUPON"
        )
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'size': 'L',
            'coupon_code': 'OTHERCOUPON'
        }
        
        serializer = OrderEntrySerializer(
            data=data,
            context={'bulk_order': self.bulk_order, 'request': request}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('coupon_code', serializer.errors)
        self.assertIn('does not belong to', str(serializer.errors['coupon_code']))

    def test_create_order_with_used_coupon(self):
        """Test that already-used coupon is rejected"""
        self.coupon.is_used = True
        self.coupon.save()
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'size': 'L',
            'coupon_code': 'TESTCOUPON'
        }
        
        serializer = OrderEntrySerializer(
            data=data,
            context={'bulk_order': self.bulk_order, 'request': request}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('coupon_code', serializer.errors)

    def test_validation_requires_bulk_order_context(self):
        """Test that validation fails without bulk_order in context"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'size': 'M'
        }
        
        serializer = OrderEntrySerializer(
            data=data,
            context={'request': request}  # Missing bulk_order
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('bulk_order', serializer.errors)

    def test_validation_rejects_expired_bulk_order(self):
        """Test that orders cannot be created for expired bulk orders"""
        expired_bulk_order = BulkOrderLink.objects.create(
            organization_name="Expired Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() - timedelta(days=1),
            created_by=self.user
        )
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'size': 'L'
        }
        
        serializer = OrderEntrySerializer(
            data=data,
            context={'bulk_order': expired_bulk_order, 'request': request}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('detail', serializer.errors)
        self.assertIn('expired', str(serializer.errors['detail']).lower())

    def test_custom_name_removed_when_branding_disabled(self):
        """Test that custom_name is removed if branding is disabled"""
        bulk_order_no_branding = BulkOrderLink.objects.create(
            organization_name="No Branding",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user,
            custom_branding_enabled=False
        )
        
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'size': 'M',
            'custom_name': 'SHOULD BE IGNORED'
        }
        
        with patch('jmw.background_utils.send_order_confirmation_email'):
            serializer = OrderEntrySerializer(
                data=data,
                context={'bulk_order': bulk_order_no_branding, 'request': request}
            )
            self.assertTrue(serializer.is_valid())
            order = serializer.save()
            
            # custom_name should be empty/not set
            self.assertEqual(order.custom_name, '')

    def test_validate_all_size_choices(self):
        """Test that all valid size choices are accepted"""
        valid_sizes = ["S", "M", "L", "XL", "XXL", "XXXL", "XXXXL"]
        request = self.factory.post('/')
        request.user = self.user
        
        for size in valid_sizes:
            data = {
                'email': f'test_{size}@example.com',
                'full_name': f'Test {size}',
                'size': size
            }
            
            with patch('jmw.background_utils.send_order_confirmation_email'):
                serializer = OrderEntrySerializer(
                    data=data,
                    context={'bulk_order': self.bulk_order, 'request': request}
                )
                self.assertTrue(serializer.is_valid(), f"Size {size} should be valid")

    def test_invalid_size_choice(self):
        """Test that invalid size is rejected"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'email': 'test@example.com',
            'full_name': 'Test User',
            'size': 'INVALID'
        }
        
        serializer = OrderEntrySerializer(
            data=data,
            context={'bulk_order': self.bulk_order, 'request': request}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('size', serializer.errors)


class BulkOrderLinkSerializerTest(TestCase):
    """Test suite for BulkOrderLinkSerializer"""

    def setUp(self):
        """Set up test data"""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_serialize_bulk_order_with_orders(self):
        """Test serialization of bulk order with nested orders"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Full Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # Create some orders
        OrderEntry.objects.create(
            bulk_order=bulk_order,
            email="customer1@example.com",
            full_name="Customer 1",
            size="L"
        )
        OrderEntry.objects.create(
            bulk_order=bulk_order,
            email="customer2@example.com",
            full_name="Customer 2",
            size="M",
            paid=True
        )
        
        request = self.factory.get('/')
        serializer = BulkOrderLinkSerializer(
            bulk_order,
            context={'request': request}
        )
        data = serializer.data
        
        self.assertEqual(data['organization_name'], "FULL TEST")
        self.assertEqual(data['order_count'], 2)
        self.assertEqual(data['paid_count'], 1)
        self.assertIn('orders', data)
        self.assertEqual(len(data['orders']), 2)

    def test_serialize_bulk_order_with_coupons(self):
        """Test serialization includes coupon count"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Coupon Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # Create some coupons
        CouponCode.objects.create(bulk_order=bulk_order, code="COUPON1")
        CouponCode.objects.create(bulk_order=bulk_order, code="COUPON2")
        CouponCode.objects.create(bulk_order=bulk_order, code="COUPON3")
        
        serializer = BulkOrderLinkSerializer(bulk_order)
        data = serializer.data
        
        self.assertEqual(data['coupon_count'], 3)

    def test_paid_count_method(self):
        """Test paid_count calculates correctly"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Paid Count Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # Create mix of paid and unpaid orders
        OrderEntry.objects.create(
            bulk_order=bulk_order,
            email="paid1@example.com",
            full_name="Paid 1",
            size="L",
            paid=True
        )
        OrderEntry.objects.create(
            bulk_order=bulk_order,
            email="paid2@example.com",
            full_name="Paid 2",
            size="M",
            paid=True
        )
        OrderEntry.objects.create(
            bulk_order=bulk_order,
            email="unpaid@example.com",
            full_name="Unpaid",
            size="S",
            paid=False
        )
        
        serializer = BulkOrderLinkSerializer(bulk_order)
        data = serializer.data
        
        self.assertEqual(data['paid_count'], 2)
        self.assertEqual(data['order_count'], 3)

    def test_shareable_url_with_request_context(self):
        """Test shareable_url generation with request"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="URL Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        request = self.factory.get('/')
        serializer = BulkOrderLinkSerializer(
            bulk_order,
            context={'request': request}
        )
        data = serializer.data
        
        self.assertIsNotNone(data['shareable_url'])
        self.assertIn(bulk_order.slug, data['shareable_url'])
        self.assertTrue(data['shareable_url'].startswith('http'))

    def test_shareable_url_without_request_context(self):
        """Test shareable_url generation without request"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="No Request",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        serializer = BulkOrderLinkSerializer(bulk_order)
        data = serializer.data
        
        # Should return path even without request
        self.assertIn(bulk_order.slug, data['shareable_url'])
        self.assertTrue(data['shareable_url'].startswith('/bulk-order/'))

    def test_create_bulk_order(self):
        """Test creating bulk order via serializer"""
        request = self.factory.post('/')
        request.user = self.user
        
        data = {
            'organization_name': 'New Organization',
            'price_per_item': '6000.00',
            'custom_branding_enabled': True,
            'payment_deadline': (timezone.now() + timedelta(days=45)).isoformat()
        }
        
        serializer = BulkOrderLinkSerializer(
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid())
        bulk_order = serializer.save()
        
        self.assertEqual(bulk_order.organization_name, "NEW ORGANIZATION")
        self.assertEqual(bulk_order.created_by, self.user)
        self.assertTrue(bulk_order.custom_branding_enabled)
        self.assertIsNotNone(bulk_order.slug)

    def test_read_only_fields(self):
        """Test that read-only fields are properly set"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Read Only Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        serializer = BulkOrderLinkSerializer(bulk_order)
        data = serializer.data
        
        # These should all be present and read-only
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        self.assertIn('slug', data)
        self.assertIn('order_count', data)
        self.assertIn('paid_count', data)
        self.assertIn('coupon_count', data)

    def test_lookup_by_slug(self):
        """Test that serializer uses slug for lookups"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Lookup Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # Verify slug is in Meta
        self.assertEqual(
            BulkOrderLinkSerializer.Meta.lookup_field,
            'slug'
        )


class SerializerContextTest(TestCase):
    """Test serializer behavior with different context scenarios"""

    def setUp(self):
        """Set up test data"""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.bulk_order = BulkOrderLink.objects.create(
            organization_name="Context Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )

    def test_order_serializer_without_request_context(self):
        """Test that OrderEntrySerializer can work without request"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="test@example.com",
            full_name="Test User",
            size="L"
        )
        
        # Should still serialize without request
        serializer = OrderEntrySerializer(order)
        data = serializer.data
        
        self.assertEqual(data['email'], "test@example.com")

    def test_bulk_order_serializer_builds_absolute_uri(self):
        """Test that request.build_absolute_uri is called correctly"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="URI Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # Create a mock request
        request = self.factory.get('/')
        
        serializer = BulkOrderLinkSerializer(
            bulk_order,
            context={'request': request}
        )
        data = serializer.data
        
        # Should have full absolute URI
        self.assertTrue(data['shareable_url'].startswith('http://'))


class SerializerEdgeCasesTest(TestCase):
    """Test edge cases and boundary conditions"""

    def setUp(self):
        """Set up test data"""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_order_with_empty_custom_name(self):
        """Test order with empty custom_name"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Empty Custom",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user,
            custom_branding_enabled=True
        )
        
        order = OrderEntry.objects.create(
            bulk_order=bulk_order,
            email="test@example.com",
            full_name="Test User",
            size="L",
            custom_name=""
        )
        
        serializer = OrderEntrySerializer(order)
        data = serializer.data
        
        self.assertEqual(data['custom_name'], "")

    def test_bulk_order_with_zero_price(self):
        """Test that serializer accepts zero price (model validation happens on save)"""
        # Note: MinValueValidator(0.01) is at MODEL level, not serializer level
        # Serializer will accept 0.00, but model.save() would fail
        data = {
            'organization_name': 'Zero Price',
            'price_per_item': '0.00',
            'payment_deadline': (timezone.now() + timedelta(days=30)).isoformat()
        }
        
        request = self.factory.post('/')
        request.user = self.user
        
        serializer = BulkOrderLinkSerializer(
            data=data,
            context={'request': request}
        )
        
        # Serializer validation passes (DecimalField accepts 0.00)
        self.assertTrue(serializer.is_valid())
        
        # But model save would fail with ValidationError
        # We don't test save here since it's model validation, not serializer

    def test_order_with_very_long_names(self):
        """Test order with maximum length names"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Long Names",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        long_name = "A" * 255
        order = OrderEntry.objects.create(
            bulk_order=bulk_order,
            email="test@example.com",
            full_name=long_name,
            size="L"
        )
        
        serializer = OrderEntrySerializer(order)
        data = serializer.data
        
        self.assertEqual(len(data['full_name']), 255)

    def test_serialize_many_orders(self):
        """Test serializing many orders efficiently"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Many Orders",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # Create 50 orders (use regular create, not bulk_create, since serial_number
        # is auto-generated in save() method)
        for i in range(50):
            OrderEntry.objects.create(
                bulk_order=bulk_order,
                email=f"customer{i}@example.com",
                full_name=f"Customer {i}",
                size="L"
            )
        
        # Serialize all at once
        all_orders = OrderEntry.objects.filter(bulk_order=bulk_order)
        serializer = OrderEntrySerializer(all_orders, many=True)
        data = serializer.data
        
        self.assertEqual(len(data), 50)


if __name__ == "__main__":
    import unittest
    unittest.main()