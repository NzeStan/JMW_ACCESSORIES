"""
Comprehensive test suite for Cart and CartItem serializers.

Tests cover:
- Serialization and deserialization
- Field validation
- Custom methods and properties
- Product type handling (polymorphism)
- Edge cases and error conditions
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import ValidationError
from decimal import Decimal
from cart.models import Cart, CartItem
from cart.serializers import CartSerializer, CartItemSerializer
from products.models import NyscKit, NyscTour, Church, Category


User = get_user_model()


class CartItemSerializerTests(TestCase):
    """Test suite for CartItemSerializer."""

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

        self.nysckit = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=self.category,
            available=True,
            out_of_stock=False
        )

        self.nysctour = NyscTour.objects.create(
            name='Lagos State',
            price=Decimal('15000.00'),
            category=self.category,
            available=True,
            out_of_stock=False
        )

        self.church = Church.objects.create(
            name='Church Choir Robe',
            church='catholic',
            price=Decimal('8000.00'),
            category=self.category,
            available=True,
            out_of_stock=False
        )

    def test_serialize_cart_item_with_nysckit(self):
        """Test serializing cart item with NyscKit product."""
        ct = ContentType.objects.get_for_model(NyscKit)
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=ct,
            object_id=self.nysckit.id,
            quantity=2
        )

        serializer = CartItemSerializer(cart_item)
        data = serializer.data

        self.assertEqual(data['id'], cart_item.id)
        self.assertEqual(data['quantity'], 2)
        self.assertEqual(Decimal(data['total_price']), Decimal('10000.00'))
        self.assertIn('product', data)
        self.assertEqual(data['product']['name'], 'NYSC Khaki Trouser')

    def test_serialize_cart_item_with_nysctour(self):
        """Test serializing cart item with NyscTour product."""
        ct = ContentType.objects.get_for_model(NyscTour)
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=ct,
            object_id=self.nysctour.id,
            quantity=1
        )

        serializer = CartItemSerializer(cart_item)
        data = serializer.data

        self.assertEqual(data['product']['name'], 'Lagos State')
        self.assertEqual(Decimal(data['total_price']), Decimal('15000.00'))

    def test_serialize_cart_item_with_church(self):
        """Test serializing cart item with Church product."""
        ct = ContentType.objects.get_for_model(Church)
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=ct,
            object_id=self.church.id,
            quantity=3
        )

        serializer = CartItemSerializer(cart_item)
        data = serializer.data

        self.assertEqual(data['product']['name'], 'Church Choir Robe')
        self.assertEqual(Decimal(data['total_price']), Decimal('24000.00'))

    def test_create_cart_item_with_valid_nysckit(self):
        """Test creating cart item with valid NyscKit data."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.nysckit.id),
            'product_type': 'nysckit',
            'quantity': 2
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        cart_item = serializer.save()
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.content_object, self.nysckit)

    def test_create_cart_item_with_valid_nysctour(self):
        """Test creating cart item with valid NyscTour data."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.nysctour.id),
            'product_type': 'nysctour',
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        cart_item = serializer.save()
        self.assertEqual(cart_item.content_object, self.nysctour)

    def test_create_cart_item_with_valid_church(self):
        """Test creating cart item with valid Church data."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.church.id),
            'product_type': 'church',
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        cart_item = serializer.save()
        self.assertEqual(cart_item.content_object, self.church)

    def test_create_cart_item_with_invalid_product_type(self):
        """Test creating cart item with invalid product type."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.nysckit.id),
            'product_type': 'invalid_type',
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(ValidationError) as context:
            serializer.save()

        self.assertIn('Invalid product type', str(context.exception))

    def test_create_cart_item_with_nonexistent_product(self):
        """Test creating cart item with non-existent product ID."""
        import uuid
        fake_id = uuid.uuid4()

        data = {
            'cart': self.cart.id,
            'product_id': str(fake_id),
            'product_type': 'nysckit',
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(ValidationError) as context:
            serializer.save()

        self.assertIn('Product not found', str(context.exception))

    def test_create_cart_item_with_unavailable_product(self):
        """Test creating cart item with unavailable product."""
        unavailable_product = NyscKit.objects.create(
            name='NYSC White Vest',
            type='vest',
            price=Decimal('2000.00'),
            category=self.category,
            available=False,  # Not available
            out_of_stock=False
        )

        data = {
            'cart': self.cart.id,
            'product_id': str(unavailable_product.id),
            'product_type': 'nysckit',
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(ValidationError) as context:
            serializer.save()

        self.assertIn('Product is not available', str(context.exception))

    def test_create_cart_item_with_out_of_stock_product(self):
        """Test creating cart item with out of stock product."""
        out_of_stock_product = NyscKit.objects.create(
            name='NYSC Cap',
            type='cap',
            price=Decimal('1500.00'),
            category=self.category,
            available=True,
            out_of_stock=True  # Out of stock
        )

        data = {
            'cart': self.cart.id,
            'product_id': str(out_of_stock_product.id),
            'product_type': 'nysckit',
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(ValidationError) as context:
            serializer.save()

        self.assertIn('Product is not available', str(context.exception))

    def test_update_or_create_cart_item(self):
        """Test that creating duplicate cart item updates quantity instead."""
        # First creation
        data = {
            'cart': self.cart.id,
            'product_id': str(self.nysckit.id),
            'product_type': 'nysckit',
            'quantity': 2
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        cart_item = serializer.save()

        # Try to add same product again
        data2 = {
            'cart': self.cart.id,
            'product_id': str(self.nysckit.id),
            'product_type': 'nysckit',
            'quantity': 3
        }

        serializer2 = CartItemSerializer(data=data2)
        self.assertTrue(serializer2.is_valid())
        cart_item2 = serializer2.save()

        # Should be the same item with updated quantity
        self.assertEqual(cart_item.id, cart_item2.id)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)

    def test_create_cart_item_with_extra_fields(self):
        """Test creating cart item with extra fields."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.nysckit.id),
            'product_type': 'nysckit',
            'quantity': 1,
            'extra_fields': {'size': 'XL', 'color': 'khaki'}
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        cart_item = serializer.save()
        self.assertEqual(cart_item.extra_fields['size'], 'XL')
        self.assertEqual(cart_item.extra_fields['color'], 'khaki')

    def test_product_id_write_only(self):
        """Test that product_id is write-only and not in serialized output."""
        ct = ContentType.objects.get_for_model(NyscKit)
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=ct,
            object_id=self.nysckit.id,
            quantity=1
        )

        serializer = CartItemSerializer(cart_item)
        data = serializer.data

        self.assertNotIn('product_id', data)
        self.assertNotIn('product_type', data)

    def test_total_price_read_only(self):
        """Test that total_price is read-only."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.nysckit.id),
            'product_type': 'nysckit',
            'quantity': 2,
            'total_price': Decimal('99999.99')  # Should be ignored
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        cart_item = serializer.save()
        # Should calculate based on product price, not provided value
        self.assertEqual(cart_item.total_price, Decimal('10000.00'))

    def test_case_insensitive_product_type(self):
        """Test that product_type is case-insensitive."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.nysckit.id),
            'product_type': 'NYSCKIT',  # Uppercase
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        cart_item = serializer.save()
        self.assertEqual(cart_item.content_object, self.nysckit)


class CartSerializerTests(TestCase):
    """Test suite for CartSerializer."""

    def setUp(self):
        """Set up test fixtures."""
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

        self.product1 = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=self.category
        )

        self.product2 = NyscKit.objects.create(
            name='NYSC White Vest',
            type='vest',
            price=Decimal('2000.00'),
            category=self.category
        )

    def test_serialize_empty_cart(self):
        """Test serializing an empty cart."""
        cart = Cart.objects.create(user=self.user)
        serializer = CartSerializer(cart)
        data = serializer.data

        self.assertEqual(str(cart.id), data['id'])
        self.assertEqual(data['user'], str(self.user.id))
        self.assertEqual(data['items'], [])
        self.assertEqual(Decimal(data['total_price']), Decimal('0'))

    def test_serialize_cart_with_items(self):
        """Test serializing cart with items."""
        cart = Cart.objects.create(user=self.user)

        ct = ContentType.objects.get_for_model(NyscKit)
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=self.product1.id,
            quantity=2
        )
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=self.product2.id,
            quantity=3
        )

        serializer = CartSerializer(cart)
        data = serializer.data

        self.assertEqual(len(data['items']), 2)
        expected_total = (Decimal('5000.00') * 2) + (Decimal('2000.00') * 3)
        self.assertEqual(Decimal(data['total_price']), expected_total)

    def test_serialize_anonymous_cart(self):
        """Test serializing an anonymous cart."""
        cart = Cart.objects.create()  # No user
        serializer = CartSerializer(cart)
        data = serializer.data

        self.assertIsNone(data['user'])
        self.assertEqual(data['items'], [])

    def test_cart_items_are_read_only(self):
        """Test that items field is read-only and cannot be set via serializer."""
        data = {
            'user': str(self.user.id),
            'items': [
                {
                    'product_id': str(self.product1.id),
                    'product_type': 'nysckit',
                    'quantity': 1
                }
            ]
        }

        serializer = CartSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        cart = serializer.save()
        # Items should not be created via cart serializer
        self.assertEqual(cart.items.count(), 0)

    def test_cart_total_price_is_read_only(self):
        """Test that total_price is read-only."""
        cart = Cart.objects.create(user=self.user)

        data = {
            'total_price': Decimal('99999.99')
        }

        serializer = CartSerializer(cart, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        serializer.save()
        cart.refresh_from_db()

        # total_price should still be 0 (no items)
        self.assertEqual(cart.total_price, Decimal('0'))

    def test_cart_includes_timestamps(self):
        """Test that cart serialization includes created_at and updated_at."""
        cart = Cart.objects.create(user=self.user)
        serializer = CartSerializer(cart)
        data = serializer.data

        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        self.assertIsNotNone(data['created_at'])
        self.assertIsNotNone(data['updated_at'])

    def test_nested_cart_item_serialization(self):
        """Test that nested cart items are properly serialized."""
        cart = Cart.objects.create(user=self.user)

        ct = ContentType.objects.get_for_model(NyscKit)
        cart_item = CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=self.product1.id,
            quantity=2
        )

        serializer = CartSerializer(cart)
        data = serializer.data

        self.assertEqual(len(data['items']), 1)
        item_data = data['items'][0]

        self.assertEqual(item_data['id'], cart_item.id)
        self.assertEqual(item_data['quantity'], 2)
        self.assertIn('product', item_data)
        self.assertEqual(Decimal(item_data['total_price']), Decimal('10000.00'))


class CartItemSerializerEdgeCaseTests(TestCase):
    """Test edge cases and error conditions for serializers."""

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
            category=self.category,
            available=True,
            out_of_stock=False
        )

    def test_create_cart_item_without_product_id(self):
        """Test creating cart item without product_id raises validation error."""
        data = {
            'cart': self.cart.id,
            'product_type': 'nysckit',
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('product_id', serializer.errors)

    def test_create_cart_item_without_product_type(self):
        """Test creating cart item without product_type raises validation error."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.product.id),
            'quantity': 1
        }

        serializer = CartItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('product_type', serializer.errors)

    def test_create_cart_item_with_zero_quantity(self):
        """Test creating cart item with zero quantity."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.product.id),
            'product_type': 'nysckit',
            'quantity': 0
        }

        serializer = CartItemSerializer(data=data)
        # Django's PositiveIntegerField validation should handle this
        self.assertFalse(serializer.is_valid())

    def test_create_cart_item_with_negative_quantity(self):
        """Test creating cart item with negative quantity."""
        data = {
            'cart': self.cart.id,
            'product_id': str(self.product.id),
            'product_type': 'nysckit',
            'quantity': -5
        }

        serializer = CartItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_multiple_product_types_in_single_cart(self):
        """Test serializing cart with multiple product types."""
        tour = NyscTour.objects.create(
            name='Lagos State',
            price=Decimal('15000.00'),
            category=self.category
        )

        church = Church.objects.create(
            name='Church Choir Robe',
            church='catholic',
            price=Decimal('8000.00'),
            category=self.category
        )

        # Add different product types
        nysckit_ct = ContentType.objects.get_for_model(NyscKit)
        tour_ct = ContentType.objects.get_for_model(NyscTour)
        church_ct = ContentType.objects.get_for_model(Church)

        CartItem.objects.create(
            cart=self.cart,
            content_type=nysckit_ct,
            object_id=self.product.id,
            quantity=1
        )
        CartItem.objects.create(
            cart=self.cart,
            content_type=tour_ct,
            object_id=tour.id,
            quantity=1
        )
        CartItem.objects.create(
            cart=self.cart,
            content_type=church_ct,
            object_id=church.id,
            quantity=1
        )

        serializer = CartSerializer(self.cart)
        data = serializer.data

        self.assertEqual(len(data['items']), 3)

        # Verify all products are properly serialized
        product_names = [item['product']['name'] for item in data['items']]
        self.assertIn('NYSC Khaki Trouser', product_names)
        self.assertIn('Lagos State', product_names)
        self.assertIn('Church Choir Robe', product_names)

        # Verify total
        expected_total = Decimal('5000.00') + Decimal('15000.00') + Decimal('8000.00')
        self.assertEqual(Decimal(data['total_price']), expected_total)
