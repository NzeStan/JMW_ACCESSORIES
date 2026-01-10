from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.contrib.contenttypes.models import ContentType

from .models import Order, OrderItem
from cart.models import Cart, CartItem
from products.models import NyscKit, Category

User = get_user_model()


class OrderModelTest(TestCase):
    """Test cases for the Order model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

    def test_order_creation(self):
        """Test that an order can be created successfully."""
        order = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            address="123 Test St",
            city="Lagos",
            state="Lagos",
            total_cost=Decimal("5000.00")
        )
        self.assertIsNotNone(order.id)
        self.assertIsNotNone(order.reference)
        self.assertTrue(order.reference.startswith("JMW-ORD-"))

    def test_reference_auto_generation(self):
        """Test that reference is auto-generated on save."""
        order = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00")
        )
        self.assertTrue(order.reference)
        self.assertIn("JMW-ORD-", order.reference)

    def test_reference_uniqueness(self):
        """Test that references are unique."""
        order1 = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00")
        )
        order2 = Order.objects.create(
            user=self.user,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone_number="08087654321",
            total_cost=Decimal("3000.00")
        )
        self.assertNotEqual(order1.reference, order2.reference)

    def test_order_string_representation(self):
        """Test the string representation of an order."""
        order = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00")
        )
        expected = f"Order {order.reference}"
        self.assertEqual(str(order), expected)

    def test_ordering_by_created(self):
        """Test that orders are ordered by created descending."""
        order1 = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00")
        )
        order2 = Order.objects.create(
            user=self.user,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone_number="08087654321",
            total_cost=Decimal("3000.00")
        )
        orders = Order.objects.all()
        self.assertEqual(orders[0], order2)
        self.assertEqual(orders[1], order1)

    def test_default_status_is_pending(self):
        """Test that default status is 'pending'."""
        order = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00")
        )
        self.assertEqual(order.status, 'pending')
        self.assertFalse(order.paid)

    def test_get_total_cost_method(self):
        """Test get_total_cost method."""
        order = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00")
        )

        # Create a category and product for testing
        category = Category.objects.create(name="Test Category", slug="test-category")
        product = NyscKit.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal("1000.00"),
            category=category,
            type="kakhi"
        )

        content_type = ContentType.objects.get_for_model(NyscKit)

        # Add order items
        OrderItem.objects.create(
            order=order,
            content_type=content_type,
            object_id=product.id,
            price=Decimal("1000.00"),
            quantity=2
        )
        OrderItem.objects.create(
            order=order,
            content_type=content_type,
            object_id=product.id,
            price=Decimal("1500.00"),
            quantity=3
        )

        total = order.get_total_cost()
        self.assertEqual(total, Decimal("6500.00"))


class OrderItemModelTest(TestCase):
    """Test cases for the OrderItem model."""

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
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.product = NyscKit.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal("1000.00"),
            category=self.category,
            type="kakhi"
        )
        self.content_type = ContentType.objects.get_for_model(NyscKit)

    def test_order_item_creation(self):
        """Test that an order item can be created."""
        item = OrderItem.objects.create(
            order=self.order,
            content_type=self.content_type,
            object_id=self.product.id,
            price=Decimal("1000.00"),
            quantity=2
        )
        self.assertIsNotNone(item.id)
        self.assertEqual(item.order, self.order)
        self.assertEqual(item.product, self.product)

    def test_get_cost_method(self):
        """Test get_cost method calculates correctly."""
        item = OrderItem.objects.create(
            order=self.order,
            content_type=self.content_type,
            object_id=self.product.id,
            price=Decimal("1000.00"),
            quantity=3
        )
        self.assertEqual(item.get_cost(), Decimal("3000.00"))

    def test_get_cost_handles_none_price(self):
        """Test get_cost handles None price gracefully."""
        item = OrderItem(
            order=self.order,
            content_type=self.content_type,
            object_id=self.product.id,
            price=None,
            quantity=3
        )
        self.assertEqual(item.get_cost(), 0)

    def test_order_item_string_representation(self):
        """Test the string representation of an order item."""
        item = OrderItem.objects.create(
            order=self.order,
            content_type=self.content_type,
            object_id=self.product.id,
            price=Decimal("1000.00"),
            quantity=2
        )
        expected = f"2 x {self.product} (Order: {self.order.reference})"
        self.assertEqual(str(item), expected)


class OrderAPITest(APITestCase):
    """Test cases for the Order API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.product = NyscKit.objects.create(
            name="Test Product",
            slug="test-product",
            price=Decimal("1000.00"),
            category=self.category,
            type="kakhi"
        )
        self.content_type = ContentType.objects.get_for_model(NyscKit)

    @patch('order.serializers.send_order_confirmation_email_async')
    @patch('order.serializers.generate_order_confirmation_pdf_task')
    def test_create_order_from_cart(self, mock_pdf, mock_email):
        """Test creating an order from a cart."""
        self.client.force_authenticate(user=self.user)

        # Create cart with items
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=2,
            extra_fields={"size": "M"}
        )

        # Create order
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_number": "08012345678",
            "address": "123 Test St",
            "city": "Lagos",
            "state": "Lagos"
        }

        response = self.client.post('/api/order/orders/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('reference', response.data)
        self.assertEqual(Order.objects.count(), 1)

        # Verify cart is cleared
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)

        # Verify background tasks were called
        mock_email.assert_called_once()
        mock_pdf.assert_called_once()

    def test_create_order_requires_authentication(self):
        """Test that creating an order requires authentication for cart-based orders."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_number": "08012345678",
            "address": "123 Test St",
            "city": "Lagos",
            "state": "Lagos"
        }

        response = self.client.post('/api/order/orders/', data)

        # Should fail because user has no cart
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_with_empty_cart_fails(self):
        """Test that creating an order with empty cart fails."""
        self.client.force_authenticate(user=self.user)

        # Create empty cart
        Cart.objects.create(user=self.user)

        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_number": "08012345678",
            "address": "123 Test St",
            "city": "Lagos",
            "state": "Lagos"
        }

        response = self.client.post('/api/order/orders/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cart is empty", str(response.data))

    def test_order_list_requires_authentication(self):
        """Test that listing orders requires authentication."""
        response = self.client.get('/api/order/orders/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_only_see_own_orders(self):
        """Test that users can only see their own orders."""
        user2 = User.objects.create_user(
            username="testuser2",
            email="user2@example.com",
            password="testpass123"
        )

        order1 = Order.objects.create(
            user=self.user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="08012345678",
            total_cost=Decimal("5000.00")
        )
        order2 = Order.objects.create(
            user=user2,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone_number="08087654321",
            total_cost=Decimal("3000.00")
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/order/orders/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination
        order_ids = [order['id'] for order in response.data.get('results', response.data)]
        self.assertIn(str(order1.id), order_ids)
        self.assertNotIn(str(order2.id), order_ids)
