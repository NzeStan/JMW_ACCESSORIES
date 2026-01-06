"""
Comprehensive test suite for Cart and CartItem viewsets.

Tests cover:
- API endpoint functionality (CRUD operations)
- Authentication and permissions
- Query filtering and optimization
- Custom actions
- Edge cases and error handling
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from cart.models import Cart, CartItem
from products.models import NyscKit, NyscTour, Church, Category


User = get_user_model()


class CartViewSetTests(TestCase):
    """Test suite for CartViewSet."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )

        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
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

    def test_create_cart_authenticated(self):
        """Test creating a cart as authenticated user."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post('/api/cart/carts/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['user'], str(self.user1.id))

    def test_create_cart_anonymous(self):
        """Test creating a cart as anonymous user."""
        response = self.client.post('/api/cart/carts/')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertIsNone(response.data['user'])

    def test_retrieve_cart_by_id(self):
        """Test retrieving a cart by its ID."""
        cart = Cart.objects.create(user=self.user1)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/cart/carts/{cart.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(cart.id))

    def test_retrieve_other_user_cart_fails(self):
        """Test that user cannot retrieve another user's cart."""
        cart = Cart.objects.create(user=self.user1)

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f'/api/cart/carts/{cart.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_anonymous_cart_by_id(self):
        """Test retrieving anonymous cart by ID."""
        cart = Cart.objects.create()  # No user

        response = self.client.get(f'/api/cart/carts/{cart.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(cart.id))

    def test_delete_cart(self):
        """Test deleting a cart."""
        cart = Cart.objects.create(user=self.user1)

        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f'/api/cart/carts/{cart.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cart.objects.filter(id=cart.id).exists())

    def test_delete_other_user_cart_fails(self):
        """Test that user cannot delete another user's cart."""
        cart = Cart.objects.create(user=self.user1)

        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(f'/api/cart/carts/{cart.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Cart.objects.filter(id=cart.id).exists())

    def test_mine_action_authenticated(self):
        """Test /mine action for authenticated user."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/cart/carts/mine/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], str(self.user1.id))

        # Verify cart was created
        cart = Cart.objects.get(user=self.user1)
        self.assertIsNotNone(cart)

    def test_mine_action_creates_cart_if_not_exists(self):
        """Test that /mine creates cart if user doesn't have one."""
        self.client.force_authenticate(user=self.user1)

        # Ensure no cart exists
        self.assertFalse(Cart.objects.filter(user=self.user1).exists())

        response = self.client.get('/api/cart/carts/mine/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Cart.objects.filter(user=self.user1).exists())

    def test_mine_action_returns_existing_cart(self):
        """Test that /mine returns existing cart without creating new one."""
        cart = Cart.objects.create(user=self.user1)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/cart/carts/mine/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(cart.id))

        # Verify only one cart exists
        self.assertEqual(Cart.objects.filter(user=self.user1).count(), 1)

    def test_mine_action_unauthenticated_fails(self):
        """Test that /mine requires authentication."""
        response = self.client.get('/api/cart/carts/mine/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cart_with_items_in_response(self):
        """Test that cart response includes items."""
        cart = Cart.objects.create(user=self.user1)

        ct = ContentType.objects.get_for_model(NyscKit)
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=self.product.id,
            quantity=2
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/cart/carts/{cart.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['quantity'], 2)

    def test_cart_total_price_in_response(self):
        """Test that cart response includes total price."""
        cart = Cart.objects.create(user=self.user1)

        ct = ContentType.objects.get_for_model(NyscKit)
        CartItem.objects.create(
            cart=cart,
            content_type=ct,
            object_id=self.product.id,
            quantity=2
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/cart/carts/{cart.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['total_price']), Decimal('10000.00'))


class CartItemViewSetTests(TestCase):
    """Test suite for CartItemViewSet."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )

        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        self.cart1 = Cart.objects.create(user=self.user1)
        self.cart2 = Cart.objects.create(user=self.user2)

        self.category = Category.objects.create(
            name='NYSC Kits',
            slug='nysc-kits',
            product_type='nysc_kit'
        )

        self.product1 = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=self.category,
            available=True,
            out_of_stock=False
        )

        self.product2 = NyscKit.objects.create(
            name='NYSC White Vest',
            type='vest',
            price=Decimal('2000.00'),
            category=self.category,
            available=True,
            out_of_stock=False
        )

    def test_create_cart_item_authenticated(self):
        """Test creating cart item as authenticated user."""
        self.client.force_authenticate(user=self.user1)

        data = {
            'product_id': str(self.product1.id),
            'product_type': 'nysckit',
            'quantity': 2
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['quantity'], 2)
        self.assertEqual(response.data['product']['name'], 'NYSC Khaki Trouser')

    def test_create_cart_item_auto_creates_cart(self):
        """Test that creating cart item auto-creates cart for authenticated user."""
        # User without cart
        user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123'
        )

        self.client.force_authenticate(user=user3)
        self.assertFalse(Cart.objects.filter(user=user3).exists())

        data = {
            'product_id': str(self.product1.id),
            'product_type': 'nysckit',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Cart.objects.filter(user=user3).exists())

    def test_create_cart_item_with_explicit_cart(self):
        """Test creating cart item with explicit cart ID."""
        anonymous_cart = Cart.objects.create()  # Anonymous cart

        data = {
            'cart': str(anonymous_cart.id),
            'product_id': str(self.product1.id),
            'product_type': 'nysckit',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_cart_item_with_unavailable_product(self):
        """Test creating cart item with unavailable product."""
        unavailable_product = NyscKit.objects.create(
            name='NYSC Cap',
            type='cap',
            price=Decimal('1500.00'),
            category=self.category,
            available=False
        )

        self.client.force_authenticate(user=self.user1)

        data = {
            'product_id': str(unavailable_product.id),
            'product_type': 'nysckit',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_cart_items_authenticated(self):
        """Test listing cart items for authenticated user."""
        ct = ContentType.objects.get_for_model(NyscKit)
        CartItem.objects.create(
            cart=self.cart1,
            content_type=ct,
            object_id=self.product1.id,
            quantity=1
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/cart/items/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_cart_items_filters_by_user(self):
        """Test that users only see their own cart items."""
        ct = ContentType.objects.get_for_model(NyscKit)

        # Create items for both users
        CartItem.objects.create(
            cart=self.cart1,
            content_type=ct,
            object_id=self.product1.id,
            quantity=1
        )
        CartItem.objects.create(
            cart=self.cart2,
            content_type=ct,
            object_id=self.product2.id,
            quantity=1
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get('/api/cart/items/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['product']['name'], 'NYSC Khaki Trouser')

    def test_list_cart_items_unauthenticated_returns_empty(self):
        """Test that anonymous users get empty list."""
        response = self.client.get('/api/cart/items/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_retrieve_cart_item(self):
        """Test retrieving a specific cart item."""
        ct = ContentType.objects.get_for_model(NyscKit)
        cart_item = CartItem.objects.create(
            cart=self.cart1,
            content_type=ct,
            object_id=self.product1.id,
            quantity=2
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/cart/items/{cart_item.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quantity'], 2)

    def test_update_cart_item_quantity(self):
        """Test updating cart item quantity."""
        ct = ContentType.objects.get_for_model(NyscKit)
        cart_item = CartItem.objects.create(
            cart=self.cart1,
            content_type=ct,
            object_id=self.product1.id,
            quantity=2
        )

        self.client.force_authenticate(user=self.user1)

        data = {
            'quantity': 5
        }

        response = self.client.patch(f'/api/cart/items/{cart_item.id}/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quantity'], 5)

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)

    def test_delete_cart_item(self):
        """Test deleting a cart item."""
        ct = ContentType.objects.get_for_model(NyscKit)
        cart_item = CartItem.objects.create(
            cart=self.cart1,
            content_type=ct,
            object_id=self.product1.id,
            quantity=1
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(f'/api/cart/items/{cart_item.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_cannot_access_other_user_cart_item(self):
        """Test that user cannot access another user's cart items."""
        ct = ContentType.objects.get_for_model(NyscKit)
        cart_item = CartItem.objects.create(
            cart=self.cart2,  # user2's cart
            content_type=ct,
            object_id=self.product1.id,
            quantity=1
        )

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f'/api/cart/items/{cart_item.id}/')

        # Should NOT be able to access another user's cart item
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_multiple_items_in_cart(self):
        """Test adding multiple different products to cart."""
        self.client.force_authenticate(user=self.user1)

        # Add first product
        data1 = {
            'product_id': str(self.product1.id),
            'product_type': 'nysckit',
            'quantity': 2
        }
        response1 = self.client.post('/api/cart/items/', data1)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Add second product
        data2 = {
            'product_id': str(self.product2.id),
            'product_type': 'nysckit',
            'quantity': 3
        }
        response2 = self.client.post('/api/cart/items/', data2)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)

        # Verify both items exist
        self.assertEqual(CartItem.objects.filter(cart=self.cart1).count(), 2)

    def test_create_duplicate_item_updates_quantity(self):
        """Test that adding same product updates existing cart item."""
        self.client.force_authenticate(user=self.user1)

        # Add product first time
        data = {
            'product_id': str(self.product1.id),
            'product_type': 'nysckit',
            'quantity': 2
        }
        response1 = self.client.post('/api/cart/items/', data)
        item_id = response1.data['id']

        # Add same product again
        data['quantity'] = 5
        response2 = self.client.post('/api/cart/items/', data)

        # Should be same item with updated quantity
        self.assertEqual(response2.data['id'], item_id)
        self.assertEqual(response2.data['quantity'], 5)
        self.assertEqual(CartItem.objects.filter(cart=self.cart1).count(), 1)


class CartItemViewSetProductTypeTests(TestCase):
    """Test suite for different product types in cart items."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()

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

        self.nysckit = NyscKit.objects.create(
            name='NYSC Khaki Trouser',
            type='kakhi',
            price=Decimal('5000.00'),
            category=self.category
        )

        self.nysctour = NyscTour.objects.create(
            name='Lagos State',
            price=Decimal('15000.00'),
            category=self.category
        )

        self.church = Church.objects.create(
            name='Church Choir Robe',
            church='catholic',
            price=Decimal('8000.00'),
            category=self.category
        )

    def test_add_nysckit_to_cart(self):
        """Test adding NyscKit product to cart."""
        self.client.force_authenticate(user=self.user)

        data = {
            'product_id': str(self.nysckit.id),
            'product_type': 'nysckit',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['product']['name'], 'NYSC Khaki Trouser')

    def test_add_nysctour_to_cart(self):
        """Test adding NyscTour product to cart."""
        self.client.force_authenticate(user=self.user)

        data = {
            'product_id': str(self.nysctour.id),
            'product_type': 'nysctour',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['product']['name'], 'Lagos State')

    def test_add_church_to_cart(self):
        """Test adding Church product to cart."""
        self.client.force_authenticate(user=self.user)

        data = {
            'product_id': str(self.church.id),
            'product_type': 'church',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['product']['name'], 'Church Choir Robe')

    def test_add_mixed_product_types_to_cart(self):
        """Test adding different product types to same cart."""
        self.client.force_authenticate(user=self.user)

        # Add NyscKit
        data1 = {
            'product_id': str(self.nysckit.id),
            'product_type': 'nysckit',
            'quantity': 1
        }
        self.client.post('/api/cart/items/', data1)

        # Add NyscTour
        data2 = {
            'product_id': str(self.nysctour.id),
            'product_type': 'nysctour',
            'quantity': 1
        }
        self.client.post('/api/cart/items/', data2)

        # Add Church
        data3 = {
            'product_id': str(self.church.id),
            'product_type': 'church',
            'quantity': 1
        }
        self.client.post('/api/cart/items/', data3)

        # Verify all three items in cart
        response = self.client.get('/api/cart/items/')
        self.assertEqual(len(response.data), 3)

    def test_invalid_product_type(self):
        """Test adding item with invalid product type."""
        self.client.force_authenticate(user=self.user)

        data = {
            'product_id': str(self.nysckit.id),
            'product_type': 'invalid_type',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CartItemViewSetEdgeCaseTests(TestCase):
    """Test edge cases and error conditions for cart item views."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()

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

    def test_create_cart_item_without_auth_and_cart_id(self):
        """Test creating cart item without authentication and no cart ID."""
        data = {
            'product_id': str(self.product.id),
            'product_type': 'nysckit',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        # Should fail because no cart is specified
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_cart_item_with_nonexistent_product(self):
        """Test creating cart item with non-existent product."""
        import uuid

        self.client.force_authenticate(user=self.user)

        data = {
            'product_id': str(uuid.uuid4()),
            'product_type': 'nysckit',
            'quantity': 1
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_cart_item_with_zero_quantity(self):
        """Test creating cart item with zero quantity."""
        self.client.force_authenticate(user=self.user)

        data = {
            'product_id': str(self.product.id),
            'product_type': 'nysckit',
            'quantity': 0
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_cart_item_with_negative_quantity(self):
        """Test creating cart item with negative quantity."""
        self.client.force_authenticate(user=self.user)

        data = {
            'product_id': str(self.product.id),
            'product_type': 'nysckit',
            'quantity': -5
        }

        response = self.client.post('/api/cart/items/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_cart_item_to_zero_quantity(self):
        """Test updating cart item to zero quantity."""
        ct = ContentType.objects.get_for_model(NyscKit)
        cart_item = CartItem.objects.create(
            cart=self.cart,
            content_type=ct,
            object_id=self.product.id,
            quantity=5
        )

        self.client.force_authenticate(user=self.user)

        data = {'quantity': 0}
        response = self.client.patch(f'/api/cart/items/{cart_item.id}/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_nonexistent_cart_item(self):
        """Test retrieving non-existent cart item."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get('/api/cart/items/99999/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_cart_item(self):
        """Test deleting non-existent cart item."""
        self.client.force_authenticate(user=self.user)

        response = self.client.delete('/api/cart/items/99999/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
