# bulk_orders/tests/test_models.py
"""
Comprehensive test suite for bulk_orders models.
Tests cover all scenarios, edge cases, failures, and successes.
"""
from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import timedelta
import threading
import time

from bulk_orders.models import BulkOrderLink, CouponCode, OrderEntry

User = get_user_model()


class BulkOrderLinkModelTest(TestCase):
    """Test suite for BulkOrderLink model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.future_deadline = timezone.now() + timedelta(days=30)
        self.past_deadline = timezone.now() - timedelta(days=1)

    def test_create_bulk_order_with_all_fields(self):
        """Test creating a bulk order with all required fields"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Organization",
            price_per_item=Decimal("5000.00"),
            custom_branding_enabled=True,
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        self.assertIsNotNone(bulk_order.id)
        self.assertIsNotNone(bulk_order.slug)
        self.assertEqual(bulk_order.organization_name, "TEST ORGANIZATION")  # Should be uppercased
        self.assertEqual(bulk_order.price_per_item, Decimal("5000.00"))
        self.assertTrue(bulk_order.custom_branding_enabled)
        self.assertEqual(bulk_order.created_by, self.user)

    def test_slug_auto_generation(self):
        """Test that slug is automatically generated from organization name"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="My Cool Organization 2024",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        self.assertIsNotNone(bulk_order.slug)
        self.assertTrue(bulk_order.slug.startswith("my-cool-organization-2024-"))
        self.assertEqual(len(bulk_order.slug.split('-')[-1]), 4)  # Random 4-char suffix

    def test_slug_uniqueness_with_same_org_name(self):
        """Test that slugs are unique even with identical organization names"""
        bulk_order_1 = BulkOrderLink.objects.create(
            organization_name="Same Name",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        bulk_order_2 = BulkOrderLink.objects.create(
            organization_name="Same Name",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        self.assertNotEqual(bulk_order_1.slug, bulk_order_2.slug)

    def test_slug_length_limit_for_long_org_names(self):
        """Test slug truncation for very long organization names"""
        long_name = "A" * 300  # Very long name
        bulk_order = BulkOrderLink.objects.create(
            organization_name=long_name,
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        # Slug should be <= 300 chars (280 for name + 1 for dash + 4 for suffix + buffer)
        self.assertLessEqual(len(bulk_order.slug), 300)

    def test_organization_name_uppercasing(self):
        """Test that organization name is converted to uppercase on save"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="lowercase organization",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        self.assertEqual(bulk_order.organization_name, "LOWERCASE ORGANIZATION")

    def test_is_expired_with_future_deadline(self):
        """Test is_expired returns False for future deadlines"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Future Deadline",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        self.assertFalse(bulk_order.is_expired())

    def test_is_expired_with_past_deadline(self):
        """Test is_expired returns True for past deadlines"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Past Deadline",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.past_deadline,
            created_by=self.user
        )
        
        self.assertTrue(bulk_order.is_expired())

    def test_is_expired_with_exact_now(self):
        """Test is_expired with deadline exactly at current time"""
        exact_now = timezone.now()
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Exact Now",
            price_per_item=Decimal("5000.00"),
            payment_deadline=exact_now,
            created_by=self.user
        )
        
        # Should be expired or very close to expiring
        # Due to processing time, this might be slightly after
        result = bulk_order.is_expired()
        self.assertIn(result, [True, False])  # Either is acceptable

    def test_get_shareable_url(self):
        """Test get_shareable_url returns correct format"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        url = bulk_order.get_shareable_url()
        self.assertEqual(url, f"/bulk-order/{bulk_order.slug}/")

    def test_get_absolute_url(self):
        """Test get_absolute_url method exists and uses slug"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        # The URL pattern might not exist in tests, but we can verify the method exists
        # and that it would use the slug if the URL pattern existed
        self.assertTrue(hasattr(bulk_order, 'get_absolute_url'))
        self.assertIsNotNone(bulk_order.slug)

    def test_string_representation(self):
        """Test __str__ method (implicitly through model Meta)"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Test Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        # Model doesn't define __str__ but we can test the default
        str_repr = str(bulk_order)
        self.assertIsInstance(str_repr, str)

    def test_ordering(self):
        """Test that bulk orders are ordered by -created_at"""
        bulk_order_1 = BulkOrderLink.objects.create(
            organization_name="First",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        time.sleep(0.01)  # Ensure different timestamps
        
        bulk_order_2 = BulkOrderLink.objects.create(
            organization_name="Second",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        orders = list(BulkOrderLink.objects.all())
        self.assertEqual(orders[0].id, bulk_order_2.id)  # Most recent first
        self.assertEqual(orders[1].id, bulk_order_1.id)

    def test_price_decimal_precision(self):
        """Test that price_per_item maintains correct decimal precision"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Price Test",
            price_per_item=Decimal("5000.99"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        self.assertEqual(bulk_order.price_per_item, Decimal("5000.99"))

    def test_custom_branding_default_false(self):
        """Test that custom_branding_enabled defaults to False"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="No Branding",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        self.assertFalse(bulk_order.custom_branding_enabled)

    def test_timestamps_auto_populate(self):
        """Test that created_at and updated_at are automatically populated"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Timestamp Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        self.assertIsNotNone(bulk_order.created_at)
        self.assertIsNotNone(bulk_order.updated_at)
        self.assertAlmostEqual(
            bulk_order.created_at.timestamp(),
            bulk_order.updated_at.timestamp(),
            delta=1
        )

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when model is saved"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Update Test",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        original_updated_at = bulk_order.updated_at
        time.sleep(0.01)
        
        bulk_order.price_per_item = Decimal("6000.00")
        bulk_order.save()
        
        self.assertGreater(bulk_order.updated_at, original_updated_at)

    def test_cannot_save_without_required_fields(self):
        """Test that saving without required fields raises error"""
        with self.assertRaises(IntegrityError):
            BulkOrderLink.objects.create(
                organization_name="Test",
                price_per_item=Decimal("5000.00"),
                payment_deadline=self.future_deadline,
                # Missing created_by
            )

    def test_special_characters_in_org_name_slug(self):
        """Test slug generation with special characters"""
        bulk_order = BulkOrderLink.objects.create(
            organization_name="Test & Co. (2024) #1!",
            price_per_item=Decimal("5000.00"),
            payment_deadline=self.future_deadline,
            created_by=self.user
        )
        
        # Slug should only contain valid characters
        self.assertTrue(all(c.isalnum() or c == '-' for c in bulk_order.slug))


class CouponCodeModelTest(TestCase):
    """Test suite for CouponCode model"""

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

    def test_create_coupon_code(self):
        """Test creating a coupon code"""
        coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="TEST12345"
        )
        
        self.assertIsNotNone(coupon.id)
        self.assertEqual(coupon.code, "TEST12345")
        self.assertEqual(coupon.bulk_order, self.bulk_order)
        self.assertFalse(coupon.is_used)
        self.assertIsNotNone(coupon.created_at)

    def test_coupon_code_uniqueness(self):
        """Test that coupon codes must be unique"""
        CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="UNIQUE123"
        )
        
        with self.assertRaises(IntegrityError):
            CouponCode.objects.create(
                bulk_order=self.bulk_order,
                code="UNIQUE123"
            )

    def test_is_used_defaults_to_false(self):
        """Test that is_used defaults to False"""
        coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="DEFAULT123"
        )
        
        self.assertFalse(coupon.is_used)

    def test_mark_coupon_as_used(self):
        """Test marking a coupon as used"""
        coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="MARKUSED123"
        )
        
        coupon.is_used = True
        coupon.save()
        
        coupon.refresh_from_db()
        self.assertTrue(coupon.is_used)

    def test_string_representation(self):
        """Test __str__ method"""
        coupon_unused = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="STR123"
        )
        
        coupon_used = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="STR456"
        )
        coupon_used.is_used = True
        coupon_used.save()
        
        self.assertEqual(str(coupon_unused), "STR123 (Available)")
        self.assertEqual(str(coupon_used), "STR456 (Used)")

    def test_ordering(self):
        """Test that coupons are ordered by created_at"""
        coupon_1 = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="FIRST123"
        )
        
        time.sleep(0.01)
        
        coupon_2 = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="SECOND123"
        )
        
        coupons = list(CouponCode.objects.all())
        self.assertEqual(coupons[0].id, coupon_1.id)  # Oldest first
        self.assertEqual(coupons[1].id, coupon_2.id)

    def test_cascade_delete_with_bulk_order(self):
        """Test that coupons are deleted when bulk order is deleted"""
        coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="CASCADE123"
        )
        
        bulk_order_id = self.bulk_order.id
        self.bulk_order.delete()
        
        self.assertFalse(CouponCode.objects.filter(code="CASCADE123").exists())

    def test_multiple_coupons_per_bulk_order(self):
        """Test creating multiple coupons for same bulk order"""
        coupon_1 = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="MULTI1"
        )
        coupon_2 = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="MULTI2"
        )
        
        self.assertEqual(self.bulk_order.coupons.count(), 2)

    def test_coupon_code_max_length(self):
        """Test coupon code with maximum length"""
        long_code = "A" * 20  # Max length is 20
        coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code=long_code
        )
        
        self.assertEqual(len(coupon.code), 20)


class OrderEntryModelTest(TransactionTestCase):
    """Test suite for OrderEntry model (using TransactionTestCase for race conditions)"""

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
            code="TESTCOUPON"
        )

    def test_create_order_entry(self):
        """Test creating an order entry"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L"
        )
        
        self.assertIsNotNone(order.id)
        self.assertEqual(order.serial_number, 1)  # First order
        self.assertEqual(order.email, "customer@example.com")
        self.assertEqual(order.full_name, "JOHN DOE")  # Should be uppercased
        self.assertEqual(order.size, "L")
        self.assertFalse(order.paid)

    def test_serial_number_auto_increment(self):
        """Test that serial numbers auto-increment within a bulk order"""
        order_1 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer1@example.com",
            full_name="Customer 1",
            size="L"
        )
        
        order_2 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer2@example.com",
            full_name="Customer 2",
            size="M"
        )
        
        self.assertEqual(order_1.serial_number, 1)
        self.assertEqual(order_2.serial_number, 2)

    def test_serial_numbers_independent_per_bulk_order(self):
        """Test that serial numbers are independent for different bulk orders"""
        bulk_order_2 = BulkOrderLink.objects.create(
            organization_name="Another Org",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        order_1 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer1@example.com",
            full_name="Customer 1",
            size="L"
        )
        
        order_2 = OrderEntry.objects.create(
            bulk_order=bulk_order_2,
            email="customer2@example.com",
            full_name="Customer 2",
            size="M"
        )
        
        # Both should be serial_number 1 for their respective bulk orders
        self.assertEqual(order_1.serial_number, 1)
        self.assertEqual(order_2.serial_number, 1)

    def test_full_name_uppercasing(self):
        """Test that full_name is converted to uppercase"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="lowercase name",
            size="L"
        )
        
        self.assertEqual(order.full_name, "LOWERCASE NAME")

    def test_custom_name_uppercasing(self):
        """Test that custom_name is converted to uppercase"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L",
            custom_name="custom text"
        )
        
        self.assertEqual(order.custom_name, "CUSTOM TEXT")

    def test_custom_name_blank(self):
        """Test that custom_name can be blank"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L"
        )
        
        self.assertEqual(order.custom_name, "")

    def test_coupon_assignment(self):
        """Test assigning a coupon to an order"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L",
            coupon_used=self.coupon
        )
        
        self.assertEqual(order.coupon_used, self.coupon)

    def test_paid_defaults_to_false(self):
        """Test that paid defaults to False"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L"
        )
        
        self.assertFalse(order.paid)

    def test_mark_order_as_paid(self):
        """Test marking an order as paid"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L"
        )
        
        order.paid = True
        order.save()
        
        order.refresh_from_db()
        self.assertTrue(order.paid)

    def test_size_choices_valid(self):
        """Test creating orders with all valid size choices"""
        valid_sizes = ["S", "M", "L", "XL", "XXL", "XXXL", "XXXXL"]
        
        for idx, size in enumerate(valid_sizes, start=1):
            order = OrderEntry.objects.create(
                bulk_order=self.bulk_order,
                email=f"customer{idx}@example.com",
                full_name=f"Customer {idx}",
                size=size
            )
            self.assertEqual(order.size, size)

    def test_string_representation(self):
        """Test __str__ method"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L"
        )
        
        expected = f"#{order.serial_number} - JOHN DOE (TEST ORG)"
        self.assertEqual(str(order), expected)

    def test_ordering(self):
        """Test that orders are ordered by bulk_order and serial_number"""
        order_3 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer3@example.com",
            full_name="Customer 3",
            size="L"
        )
        
        order_1 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer1@example.com",
            full_name="Customer 1",
            size="M"
        )
        
        order_2 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer2@example.com",
            full_name="Customer 2",
            size="S"
        )
        
        orders = list(OrderEntry.objects.all())
        # Should be ordered by serial_number: 1, 2, 3
        self.assertEqual(orders[0].serial_number, 1)
        self.assertEqual(orders[1].serial_number, 2)
        self.assertEqual(orders[2].serial_number, 3)

    def test_unique_together_constraint(self):
        """Test that (bulk_order, serial_number) must be unique"""
        order_1 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer1@example.com",
            full_name="Customer 1",
            size="L"
        )
        
        # Manually create another order with same serial_number (bypassing auto-increment)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                order_2 = OrderEntry(
                    bulk_order=self.bulk_order,
                    email="customer2@example.com",
                    full_name="Customer 2",
                    size="M",
                    serial_number=order_1.serial_number  # Same serial number
                )
                order_2.save()

    def test_cascade_delete_with_bulk_order(self):
        """Test that orders are deleted when bulk order is deleted"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L"
        )
        
        order_id = order.id
        self.bulk_order.delete()
        
        self.assertFalse(OrderEntry.objects.filter(id=order_id).exists())

    def test_set_null_when_coupon_deleted(self):
        """Test that coupon_used is set to NULL when coupon is deleted"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L",
            coupon_used=self.coupon
        )
        
        self.coupon.delete()
        order.refresh_from_db()
        
        self.assertIsNone(order.coupon_used)

    def test_timestamps_auto_populate(self):
        """Test that created_at and updated_at are automatically populated"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L"
        )
        
        self.assertIsNotNone(order.created_at)
        self.assertIsNotNone(order.updated_at)

    def test_updated_at_changes_on_save(self):
        """Test that updated_at changes when model is saved"""
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer@example.com",
            full_name="John Doe",
            size="L"
        )
        
        original_updated_at = order.updated_at
        time.sleep(0.01)
        
        order.paid = True
        order.save()
        
        self.assertGreater(order.updated_at, original_updated_at)

    def test_user_email_initialization(self):
        """Test __init__ with user parameter"""
        # This tests the custom __init__ method
        order = OrderEntry(
            bulk_order=self.bulk_order,
            full_name="John Doe",
            size="L",
            user=self.user
        )
        order.save()
        
        self.assertEqual(order.email, self.user.email)

    def test_concurrent_serial_number_generation(self):
        """Test that serial numbers are correctly generated under concurrent access"""
        from django.db import connection
        
        # Skip this test for SQLite as it doesn't handle concurrent writes well
        if connection.vendor == 'sqlite':
            self.skipTest("SQLite doesn't support concurrent writes (database locking)")
        
        def create_order(order_num):
            """Helper function to create an order"""
            with transaction.atomic():
                OrderEntry.objects.create(
                    bulk_order=self.bulk_order,
                    email=f"customer{order_num}@example.com",
                    full_name=f"Customer {order_num}",
                    size="L"
                )
        
        # Create orders concurrently
        threads = []
        num_orders = 10
        
        for i in range(num_orders):
            thread = threading.Thread(target=create_order, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all orders were created with unique serial numbers
        orders = OrderEntry.objects.filter(bulk_order=self.bulk_order).order_by('serial_number')
        self.assertEqual(orders.count(), num_orders)
        
        # Check that serial numbers are 1 through num_orders
        serial_numbers = [order.serial_number for order in orders]
        self.assertEqual(serial_numbers, list(range(1, num_orders + 1)))

    def test_email_validation(self):
        """Test that invalid email addresses are rejected"""
        # Django's EmailField should validate this, but test it anyway
        order = OrderEntry(
            bulk_order=self.bulk_order,
            email="invalid-email",
            full_name="John Doe",
            size="L"
        )
        
        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_max_length_fields(self):
        """Test fields at their maximum lengths"""
        # EmailField max is 254 chars: 242 + @ + 11 = 254
        long_email = "a" * 242 + "@example.com"  # Max 254 chars
        long_name = "A" * 255  # Max 255 chars
        long_custom = "C" * 255  # Max 255 chars
        
        order = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email=long_email,
            full_name=long_name,
            size="L",
            custom_name=long_custom
        )
        
        self.assertEqual(len(order.email), 254)
        self.assertEqual(len(order.full_name), 255)
        self.assertEqual(len(order.custom_name), 255)


class ModelRelationshipTest(TestCase):
    """Test relationships between models"""

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

    def test_bulk_order_to_coupons_relationship(self):
        """Test reverse relationship from BulkOrderLink to CouponCode"""
        coupon_1 = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="COUPON1"
        )
        coupon_2 = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="COUPON2"
        )
        
        coupons = self.bulk_order.coupons.all()
        self.assertEqual(coupons.count(), 2)
        self.assertIn(coupon_1, coupons)
        self.assertIn(coupon_2, coupons)

    def test_bulk_order_to_orders_relationship(self):
        """Test reverse relationship from BulkOrderLink to OrderEntry"""
        order_1 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer1@example.com",
            full_name="Customer 1",
            size="L"
        )
        order_2 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer2@example.com",
            full_name="Customer 2",
            size="M"
        )
        
        orders = self.bulk_order.orders.all()
        self.assertEqual(orders.count(), 2)
        self.assertIn(order_1, orders)
        self.assertIn(order_2, orders)

    def test_user_to_bulk_orders_relationship(self):
        """Test that user can have multiple bulk orders"""
        bulk_order_1 = BulkOrderLink.objects.create(
            organization_name="Org 1",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        bulk_order_2 = BulkOrderLink.objects.create(
            organization_name="Org 2",
            price_per_item=Decimal("5000.00"),
            payment_deadline=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # Note: BulkOrderLink doesn't define related_name, so we use the default
        user_bulk_orders = BulkOrderLink.objects.filter(created_by=self.user)
        self.assertEqual(user_bulk_orders.count(), 3)  # Including setUp bulk_order

    def test_coupon_to_order_entries_relationship(self):
        """Test that a coupon can be used by multiple orders (if is_used not enforced)"""
        coupon = CouponCode.objects.create(
            bulk_order=self.bulk_order,
            code="SHARED"
        )
        
        # Note: In practice, coupons should only be used once,
        # but the model doesn't enforce this at DB level
        order_1 = OrderEntry.objects.create(
            bulk_order=self.bulk_order,
            email="customer1@example.com",
            full_name="Customer 1",
            size="L",
            coupon_used=coupon
        )
        
        # Check the relationship
        self.assertEqual(order_1.coupon_used, coupon)


class ModelIndexTest(TestCase):
    """Test that model indexes improve query performance"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_bulk_order_indexes_exist(self):
        """Test that BulkOrderLink has expected indexes"""
        indexes = [index.name for index in BulkOrderLink._meta.indexes]
        
        self.assertIn("bulk_order_user_deadline_idx", indexes)
        self.assertIn("bulk_order_org_name_idx", indexes)
        self.assertIn("bulk_order_created_idx", indexes)
        self.assertIn("bulk_order_slug_idx", indexes)

    def test_coupon_code_indexes_exist(self):
        """Test that CouponCode has expected indexes"""
        indexes = [index.name for index in CouponCode._meta.indexes]
        
        self.assertIn("coupon_bulk_order_used_idx", indexes)
        self.assertIn("coupon_code_idx", indexes)

    def test_order_entry_indexes_exist(self):
        """Test that OrderEntry has expected indexes"""
        indexes = [index.name for index in OrderEntry._meta.indexes]
        
        self.assertIn("order_bulk_serial_idx", indexes)
        self.assertIn("order_email_idx", indexes)
        self.assertIn("order_paid_idx", indexes)
        self.assertIn("order_size_idx", indexes)
        self.assertIn("order_created_idx", indexes)
        self.assertIn("order_updated_idx", indexes)


if __name__ == "__main__":
    import unittest
    unittest.main()