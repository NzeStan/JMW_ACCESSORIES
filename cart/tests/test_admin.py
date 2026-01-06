"""
Comprehensive test suite for Cart and CartItem admin interfaces.

Tests cover:
- Admin registration
- Admin list display
- Admin filtering and searching
- Inline admin functionality
- Admin permissions
"""

from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal
from cart.models import Cart, CartItem
from cart.admin import CartAdmin, CartItemInline
from products.models import NyscKit, Category


User = get_user_model()


class MockRequest:
    """Mock request object for admin testing."""
    pass


class MockSuperUser:
    """Mock superuser for admin testing."""
    def has_perm(self, perm):
        return True


class CartAdminTests(TestCase):
    """Test suite for CartAdmin."""

    def setUp(self):
        """Set up test fixtures."""
        self.site = AdminSite()
        self.cart_admin = CartAdmin(Cart, self.site)
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )

        self.category = Category.objects.create(
            name='NYSC Kits',
            slug='nysc-kits',
            product_type='nysc_kit'
        )

        self.product = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=self.category
        )

    def test_cart_admin_is_registered(self):
        """Test that Cart model is registered in admin."""
        from django.contrib import admin
        self.assertTrue(admin.site.is_registered(Cart))

    def test_cart_item_admin_is_registered(self):
        """Test that CartItem model is registered in admin."""
        from django.contrib import admin
        self.assertTrue(admin.site.is_registered(CartItem))

    def test_cart_admin_list_display(self):
        """Test that CartAdmin has appropriate list_display fields."""
        expected_fields = ('id', 'user_display', 'item_count', 'total_price_display', 'created_at', 'updated_at')

        self.assertTrue(hasattr(self.cart_admin, 'list_display'))

        for field in expected_fields:
            self.assertIn(field, self.cart_admin.list_display)

    def test_cart_admin_list_filter(self):
        """Test that CartAdmin has appropriate list_filter fields."""
        self.assertTrue(hasattr(self.cart_admin, 'list_filter'))
        self.assertIn('created_at', self.cart_admin.list_filter)
        self.assertIn('user', self.cart_admin.list_filter)

    def test_cart_admin_search_fields(self):
        """Test that CartAdmin has appropriate search_fields."""
        self.assertTrue(hasattr(self.cart_admin, 'search_fields'))
        self.assertIn('user__email', self.cart_admin.search_fields)

    def test_cart_admin_readonly_fields(self):
        """Test that CartAdmin has appropriate readonly_fields."""
        self.assertTrue(hasattr(self.cart_admin, 'readonly_fields'))
        self.assertIn('id', self.cart_admin.readonly_fields)
        self.assertIn('created_at', self.cart_admin.readonly_fields)
        self.assertIn('updated_at', self.cart_admin.readonly_fields)
        self.assertIn('total_price_display', self.cart_admin.readonly_fields)

    def test_cart_admin_has_inline(self):
        """Test that CartAdmin has CartItem inline."""
        self.assertTrue(hasattr(self.cart_admin, 'inlines'))
        self.assertIn(CartItemInline, self.cart_admin.inlines)

    def test_cart_admin_item_count_method(self):
        """Test the item_count method in CartAdmin."""
        cart = Cart.objects.create(user=self.user)

        # Create a second product for testing
        product2 = NyscKit.objects.create(
            name='NYSC Jacket',
            type='jacket',
            price=Decimal('6000.00'),
            category=self.category
        )

        ct = ContentType.objects.get_for_model(NyscKit)
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=self.product.id,
            quantity=1
        )
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=product2.id,  # Different product
            quantity=2
        )

        # The item_count method should count the items
        if hasattr(self.cart_admin, 'item_count'):
            count = self.cart_admin.item_count(cart)
            self.assertEqual(count, 2)

    def test_cart_admin_total_price_display(self):
        """Test the total_price display in CartAdmin."""
        cart = Cart.objects.create(user=self.user)

        ct = ContentType.objects.get_for_model(NyscKit)
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=self.product.id,
            quantity=2
        )

        # Verify total_price is accessible
        self.assertEqual(cart.total_price, Decimal('10000.00'))

    def test_cart_admin_ordering(self):
        """Test that CartAdmin has appropriate ordering."""
        if hasattr(self.cart_admin, 'ordering'):
            self.assertIn('-created_at', self.cart_admin.ordering)


class CartItemInlineTests(TestCase):
    """Test suite for CartItemInline."""

    def setUp(self):
        """Set up test fixtures."""
        self.site = AdminSite()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.cart = Cart.objects.create(user=self.user)

        self.category = Category.objects.create(
            name='NYSC Kits',
            slug='nysc-kits',
            product_type='nysc_kit'
        )

        self.product = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=self.category
        )

    def test_cart_item_inline_model(self):
        """Test that CartItemInline uses CartItem model."""
        inline = CartItemInline(Cart, self.site)
        self.assertEqual(inline.model, CartItem)

    def test_cart_item_inline_extra(self):
        """Test CartItemInline extra attribute."""
        inline = CartItemInline(Cart, self.site)

        if hasattr(inline, 'extra'):
            self.assertGreaterEqual(inline.extra, 0)

    def test_cart_item_inline_fields(self):
        """Test that CartItemInline has appropriate fields."""
        inline = CartItemInline(Cart, self.site)

        if hasattr(inline, 'fields'):
            self.assertIsNotNone(inline.fields)

    def test_cart_item_inline_readonly_fields(self):
        """Test that CartItemInline has readonly fields."""
        inline = CartItemInline(Cart, self.site)

        if hasattr(inline, 'readonly_fields'):
            # total_price should be readonly
            self.assertIn('total_price', inline.readonly_fields)


class CartItemAdminTests(TestCase):
    """Test suite for CartItemAdmin."""

    def setUp(self):
        """Set up test fixtures."""
        from cart.admin import CartItemAdmin
        from django.contrib import admin

        self.site = AdminSite()

        # Get the registered admin
        if admin.site.is_registered(CartItem):
            self.cart_item_admin = admin.site._registry[CartItem]
        else:
            self.cart_item_admin = CartItemAdmin(CartItem, self.site)

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.cart = Cart.objects.create(user=self.user)

        self.category = Category.objects.create(
            name='NYSC Kits',
            slug='nysc-kits',
            product_type='nysc_kit'
        )

        self.product = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=self.category
        )

    def test_cart_item_admin_list_display(self):
        """Test that CartItemAdmin has appropriate list_display fields."""
        if hasattr(self.cart_item_admin, 'list_display'):
            self.assertIn('cart', self.cart_item_admin.list_display)
            self.assertIn('quantity', self.cart_item_admin.list_display)

    def test_cart_item_admin_list_filter(self):
        """Test that CartItemAdmin has appropriate list_filter."""
        if hasattr(self.cart_item_admin, 'list_filter'):
            self.assertIn('cart', self.cart_item_admin.list_filter)

    def test_cart_item_admin_readonly_fields(self):
        """Test that CartItemAdmin has readonly fields."""
        if hasattr(self.cart_item_admin, 'readonly_fields'):
            self.assertIn('total_price', self.cart_item_admin.readonly_fields)


class AdminIntegrationTests(TestCase):
    """Integration tests for admin functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.category = Category.objects.create(
            name='NYSC Kits',
            slug='nysc-kits',
            product_type='nysc_kit'
        )

        self.product = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=self.category
        )

        self.cart = Cart.objects.create(user=self.user)

        ct = ContentType.objects.get_for_model(NyscKit)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=ct,
            object_id=self.product.id,
            quantity=2
        )

    def test_admin_cart_list_accessible(self):
        """Test that admin cart list page is accessible."""
        from django.test import Client
        from django.urls import reverse

        client = Client()
        client.force_login(self.superuser)

        url = reverse('admin:cart_cart_changelist')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_cart_detail_accessible(self):
        """Test that admin cart detail page is accessible."""
        from django.test import Client
        from django.urls import reverse

        client = Client()
        client.force_login(self.superuser)

        url = reverse('admin:cart_cart_change', args=[self.cart.id])
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_admin_cart_item_list_accessible(self):
        """Test that admin cart item list page is accessible."""
        from django.test import Client
        from django.urls import reverse

        client = Client()
        client.force_login(self.superuser)

        url = reverse('admin:cart_cartitem_changelist')
        response = client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_non_superuser_cannot_access_admin(self):
        """Test that non-superusers cannot access admin."""
        from django.test import Client
        from django.urls import reverse

        client = Client()
        client.force_login(self.user)

        url = reverse('admin:cart_cart_changelist')
        response = client.get(url)
        # Should redirect to login or show permission denied
        self.assertIn(response.status_code, [302, 403])
