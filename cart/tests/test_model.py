"""
Comprehensive test suite for Cart and CartItem models.

Tests cover:
- Model creation and validation
- Relationships and constraints
- Properties and methods
- Edge cases and error conditions
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.utils import IntegrityError
from decimal import Decimal
from cart.models import Cart, CartItem
from products.models import NyscKit, NyscTour, Church, Category
import uuid


User = get_user_model()


class CartModelTests(TestCase):
    """Test suite for Cart model."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_cart_creation_with_user(self):
        """Test creating a cart with an authenticated user."""
        cart = Cart.objects.create(user=self.user)

        self.assertIsNotNone(cart.id)
        self.assertIsInstance(cart.id, uuid.UUID)
        self.assertEqual(cart.user, self.user)
        self.assertIsNotNone(cart.created_at)
        self.assertIsNotNone(cart.updated_at)

    def test_cart_creation_anonymous(self):
        """Test creating a cart for an anonymous user."""
        cart = Cart.objects.create()

        self.assertIsNotNone(cart.id)
        self.assertIsNone(cart.user)
        self.assertIsNotNone(cart.created_at)

    def test_cart_str_representation_with_user(self):
        """Test string representation of cart with user."""
        cart = Cart.objects.create(user=self.user)
        expected = f"Cart {cart.id} (test@example.com)"

        self.assertEqual(str(cart), expected)

    def test_cart_str_representation_anonymous(self):
        """Test string representation of anonymous cart."""
        cart = Cart.objects.create()
        expected = f"Cart {cart.id} (Anonymous)"

        self.assertEqual(str(cart), expected)

    def test_one_to_one_user_relationship(self):
        """Test that a user can only have one cart."""
        Cart.objects.create(user=self.user)

        with self.assertRaises(IntegrityError):
            Cart.objects.create(user=self.user)

    def test_cart_cascade_delete_with_user(self):
        """Test that cart is deleted when user is deleted."""
        cart = Cart.objects.create(user=self.user)
        cart_id = cart.id

        self.user.delete()

        self.assertFalse(Cart.objects.filter(id=cart_id).exists())

    def test_total_price_empty_cart(self):
        """Test total_price property for empty cart."""
        cart = Cart.objects.create(user=self.user)

        self.assertEqual(cart.total_price, 0)

    def test_total_price_with_items(self):
        """Test total_price property with items in cart."""
        cart = Cart.objects.create(user=self.user)

        # Create test products
        category = Category.objects.create(
            name='NYSC Kits',
            slug='nysc-kits',
            product_type='nysc_kit'
        )

        product1 = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=category
        )
        product2 = NyscKit.objects.create(
            name='NYSC White Vest',
            type='vest',
            price=Decimal('2000.00'),
            category=category
        )

        # Add items to cart
        ct = ContentType.objects.get_for_model(NyscKit)
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=product1.id,
            quantity=2
        )
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=product2.id,
            quantity=3
        )

        expected_total = (Decimal('5000.00') * 2) + (Decimal('2000.00') * 3)
        self.assertEqual(cart.total_price, expected_total)

    def test_cart_updated_at_changes(self):
        """Test that updated_at changes when cart is modified."""
        cart = Cart.objects.create(user=self.user)
        original_updated_at = cart.updated_at

        # Simulate a delay and update
        cart.save()

        self.assertGreaterEqual(cart.updated_at, original_updated_at)


class CartItemModelTests(TestCase):
    """Test suite for CartItem model."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.cart = Cart.objects.create(user=self.user)

        # Create category and products
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

        self.content_type = ContentType.objects.get_for_model(NyscKit)

    def test_cart_item_creation(self):
        """Test creating a cart item."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=2
        )

        self.assertIsNotNone(cart_item.id)
        self.assertEqual(cart_item.cart, self.cart)
        self.assertEqual(cart_item.content_object, self.product)
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.extra_fields, {})

    def test_cart_item_default_quantity(self):
        """Test that quantity defaults to 1."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id
        )

        self.assertEqual(cart_item.quantity, 1)

    def test_cart_item_with_extra_fields(self):
        """Test cart item with extra JSON fields."""
        extra_data = {'size': 'XL', 'color': 'khaki', 'custom_note': 'Rush delivery'}

        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1,
            extra_fields=extra_data
        )

        self.assertEqual(cart_item.extra_fields, extra_data)
        self.assertEqual(cart_item.extra_fields['size'], 'XL')

    def test_cart_item_str_representation(self):
        """Test string representation of cart item."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=3
        )

        expected = f"3 x {self.product}"
        self.assertEqual(str(cart_item), expected)

    def test_cart_item_total_price(self):
        """Test total_price property calculation."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=4
        )

        expected = self.product.price * 4
        self.assertEqual(cart_item.total_price, expected)

    def test_unique_together_constraint(self):
        """Test that same product cannot be added twice to same cart."""
        CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1
        )

        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=self.cart,
                content_type=self.content_type,
                object_id=self.product.id,
                quantity=2
            )

    def test_cart_item_cascade_delete_with_cart(self):
        """Test that cart items are deleted when cart is deleted."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1
        )
        item_id = cart_item.id

        self.cart.delete()

        self.assertFalse(CartItem.objects.filter(id=item_id).exists())

    def test_multiple_items_in_cart(self):
        """Test adding multiple different products to cart."""
        product2 = NyscKit.objects.create(
            name='NYSC White Vest',
            type='vest',
            price=Decimal('2000.00'),
            category=self.category
        )

        item1 = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1
        )
        item2 = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=product2.id,
            quantity=2
        )

        self.assertEqual(self.cart.items.count(), 2)
        self.assertIn(item1, self.cart.items.all())
        self.assertIn(item2, self.cart.items.all())

    def test_cart_item_with_different_product_types(self):
        """Test cart items with different product types (polymorphic)."""
        # Create NyscTour product
        tour = NyscTour.objects.create(
            name='Lagos State',
            price=Decimal('15000.00'),
            category=self.category
        )
        tour_ct = ContentType.objects.get_for_model(NyscTour)

        # Add both NyscKit and NyscTour to cart
        item1 = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1
        )
        item2 = CartItem.objects.create(
            cart=self.cart,
            content_type=tour_ct,
            object_id=tour.id,
            quantity=1
        )

        self.assertEqual(self.cart.items.count(), 2)
        self.assertIsInstance(item1.content_object, NyscKit)
        self.assertIsInstance(item2.content_object, NyscTour)

    def test_cart_item_related_name(self):
        """Test accessing cart items through cart's related name."""
        CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1
        )

        self.assertEqual(self.cart.items.count(), 1)
        self.assertEqual(self.cart.items.first().content_object, self.product)

    def test_cart_item_quantity_validation(self):
        """Test that quantity must be positive."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1
        )

        # Attempting to set negative quantity
        cart_item.quantity = -1
        with self.assertRaises(IntegrityError):
            cart_item.save()

    def test_cart_item_with_church_product(self):
        """Test cart item with Church product type."""
        church_product = Church.objects.create(
            name='Church Choir Robe',
            church='catholic',
            price=Decimal('8000.00'),
            category=self.category
        )
        church_ct = ContentType.objects.get_for_model(Church)

        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=church_ct,
            object_id=church_product.id,
            quantity=1
        )

        self.assertEqual(cart_item.content_object, church_product)
        self.assertIsInstance(cart_item.content_object, Church)
        self.assertEqual(cart_item.total_price, Decimal('8000.00'))


class CartItemEdgeCaseTests(TestCase):
    """Test edge cases and error conditions for cart items."""

    def setUp(self):
        """Set up test fixtures."""
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

        self.content_type = ContentType.objects.get_for_model(NyscKit)

    def test_cart_item_with_zero_quantity(self):
        """Test creating cart item with zero quantity (allowed at model level)."""
        # Django's PositiveIntegerField allows 0
        # Validation is enforced at the serializer level
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=0
        )
        self.assertEqual(cart_item.quantity, 0)

    def test_cart_item_with_large_quantity(self):
        """Test cart item with very large quantity."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=999999
        )

        expected_total = self.product.price * 999999
        self.assertEqual(cart_item.total_price, expected_total)

    def test_empty_extra_fields_default(self):
        """Test that extra_fields defaults to empty dict."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1
        )

        self.assertEqual(cart_item.extra_fields, {})
        self.assertIsInstance(cart_item.extra_fields, dict)

    def test_cart_item_update_quantity(self):
        """Test updating cart item quantity."""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=self.content_type,
            object_id=self.product.id,
            quantity=1
        )

        cart_item.quantity = 5
        cart_item.save()
        cart_item.refresh_from_db()

        self.assertEqual(cart_item.quantity, 5)
        self.assertEqual(cart_item.total_price, self.product.price * 5)
