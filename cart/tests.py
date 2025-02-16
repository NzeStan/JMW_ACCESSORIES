# cart/tests.py

from django.test import TestCase, Client, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.urls import reverse
from django.contrib.messages import get_messages
from django.conf import settings
from products.models import Category, NyscKit, NyscTour, Church
from .cart import Cart
from .middleware import CartCleanupMiddleware
import logging

logger = logging.getLogger(__name__)


class CartTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Create test category
        self.category = Category.objects.create(
            name="NYSC KIT", slug="nysc-kit", product_type="nysc_kit"
        )

        # Create test products
        self.nysc_kit = NyscKit.objects.create(
            name="Quality Nysc Kakhi",
            slug="quality-nysc-kakhi",
            type="kakhi",
            category=self.category,
            price=100.00,
        )

        self.nysc_tour = NyscTour.objects.create(
            name="Lagos", slug="lagos", category=self.category, price=200.00
        )

        self.church = Church.objects.create(
            name="quality_shilo_shirt",
            slug="quality-shilo-shirt",
            church="WINNERS",
            category=self.category,
            price=150.00,
        )

        # Setup request with session
        self.request = self.factory.get("/")
        self.setup_request_middlewares(self.request)

    def setup_request_middlewares(self, request):
        """Helper method to setup session and message middleware"""
        session_middleware = SessionMiddleware(lambda x: None)
        message_middleware = MessageMiddleware(lambda x: None)

        session_middleware.process_request(request)
        message_middleware.process_request(request)

        request.session.save()

    def test_add_to_cart(self):
        """Test adding items to cart"""
        cart = Cart(self.request)

        # Test adding NYSC Kit
        cart.add(product=self.nysc_kit, quantity=2, extra_fields={"size": "L"})
        self.assertEqual(len(cart), 2)

        # Test adding NYSC Tour
        cart.add(
            product=self.nysc_tour,
            quantity=1,
            extra_fields={"call_up_number": "nysc/2023/a/123456"},
        )
        self.assertEqual(len(cart), 3)

        # Verify cart contents
        cart_items = list(cart)
        self.assertEqual(len(cart_items), 2)  # Two different products

        # Check total price calculation
        expected_total = (self.nysc_kit.price * 2) + self.nysc_tour.price
        self.assertEqual(cart.get_total_price(), expected_total)

    def test_cart_update_quantity(self):
        """Test updating cart item quantities"""
        cart = Cart(self.request)

        # Add item and then update its quantity
        cart.add(product=self.nysc_kit, quantity=1)
        cart.add(product=self.nysc_kit, quantity=3, override_quantity=True)

        self.assertEqual(len(cart), 3)

    def test_cart_remove(self):
        """Test removing items from cart"""
        cart = Cart(self.request)

        # Add and then remove an item
        cart.add(product=self.nysc_kit, quantity=1)
        self.assertEqual(len(cart), 1)

        cart.remove(product=self.nysc_kit)
        self.assertEqual(len(cart), 0)

    def test_cart_clear(self):
        """Test clearing the entire cart"""
        cart = Cart(self.request)

        # Add multiple items
        cart.add(product=self.nysc_kit, quantity=1)
        cart.add(product=self.nysc_kit, quantity=2, extra_fields={"size": "XL"})
        self.assertEqual(len(cart), 3)

        # Clear cart
        cart.clear()
        self.assertEqual(len(cart), 0)

        # Verify cart is also cleared in session
        self.assertNotIn(settings.CART_SESSION_ID, self.request.session)

        # Add new item after clearing to ensure cart still works
        cart.add(product=self.nysc_kit, quantity=1)
        self.assertEqual(len(cart), 1)

    def test_cart_cleanup_deleted_products(self):
        """Test cart cleanup when products are deleted"""
        cart = Cart(self.request)

        # Add products to cart
        cart.add(product=self.nysc_kit, quantity=1)
        cart.add(product=self.nysc_tour, quantity=1)

        # Initial cart state
        self.assertEqual(len(cart), 2)

        # Delete one product
        self.nysc_kit.delete()

        # Run cleanup
        removed_items = cart.cleanup()

        # Verify cleanup results
        self.assertIsNotNone(removed_items)
        self.assertEqual(len(removed_items["deleted"]), 1)
        self.assertEqual(len(cart), 1)  # Only tour product should remain

    def test_cart_cleanup_out_of_stock(self):
        """Test cart cleanup when products go out of stock"""
        cart = Cart(self.request)

        # Add products to cart
        cart.add(product=self.nysc_kit, quantity=1)
        self.assertEqual(len(cart), 1)

        # Mark product as out of stock
        self.nysc_kit.out_of_stock = True
        self.nysc_kit.save()

        # Run cleanup
        removed_items = cart.cleanup()

        # Verify cleanup results
        self.assertIsNotNone(removed_items)
        self.assertEqual(len(removed_items["out_of_stock"]), 1)
        self.assertEqual(len(cart), 0)

    def test_cart_item_key_generation(self):
        """Test unique key generation for cart items with variations"""
        cart = Cart(self.request)

        # Add same product with different variations
        cart.add(product=self.church, quantity=1, size="M", custom_name_text="john doe")
        cart.add(product=self.church, quantity=1, size="L", custom_name_text="jane doe")

        # Should be two separate items despite being the same product
        cart_items = list(cart)
        self.assertEqual(len(cart_items), 2)

        # Get only the extra_fields for comparison
        variations = [item["extra_fields"] for item in cart_items]

        expected_variations = [
            {"size": "M", "custom_name_text": "JOHN DOE"},
            {"size": "L", "custom_name_text": "JANE DOE"},
        ]

        # Check each expected variation exists in actual variations
        for expected_var in expected_variations:
            found = False
            for var in variations:
                if var == expected_var:  # Direct dictionary comparison
                    found = True
                    break
            self.assertTrue(
                found, f"Expected variation {expected_var} not found in {variations}"
            )

    def test_uppercase_transformation(self):
        """Test that relevant fields are stored in uppercase"""
        cart = Cart(self.request)

        # Test NYSC Tour call-up number
        test_call_up = "nysc/2023/a/123456"
        cart.add(product=self.nysc_tour, quantity=1, call_up_number=test_call_up)

        cart_items = list(cart)
        self.assertTrue(cart_items, "Cart is empty")
        first_item = cart_items[0]

        self.assertIn(
            "extra_fields", first_item, f"No extra_fields in item: {first_item}"
        )
        self.assertIn(
            "call_up_number",
            first_item["extra_fields"],
            f"No call_up_number in extra_fields: {first_item['extra_fields']}",
        )

        self.assertEqual(
            first_item["extra_fields"]["call_up_number"], "NYSC/2023/A/123456"
        )

        # Test Church custom name
        test_name = "john doe"
        cart.add(product=self.church, quantity=1, size="M", custom_name_text=test_name)

        cart_items = list(cart)
        church_item = next(
            item for item in cart_items if item["product"].product_type == "church"
        )

        self.assertEqual(church_item["extra_fields"]["custom_name_text"], "JOHN DOE")

    def test_middleware_cart_cleanup(self):
        """Test that the middleware properly cleans up the cart"""
        # Create request
        request = self.factory.get("/")
        self.setup_request_middlewares(request)

        # Add items to cart
        cart = Cart(request)
        cart.add(product=self.nysc_kit, quantity=1)
        cart.add(product=self.nysc_tour, quantity=1)

        # Delete one product and mark another as out of stock
        self.nysc_kit.delete()
        self.nysc_tour.out_of_stock = True
        self.nysc_tour.save()

        # Run middleware
        middleware = CartCleanupMiddleware(lambda x: None)
        middleware(request)

        # Check messages
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertIn("Your cart has been updated", str(messages[0]))

        # Verify cart state
        cart = Cart(request)
        self.assertEqual(len(cart), 0)

    def test_add_unavailable_product(self):
        """Test adding unavailable products to cart"""
        cart = Cart(self.request)

        # Test out of stock product
        self.nysc_kit.out_of_stock = True
        self.nysc_kit.save()

        cart.add(product=self.nysc_kit, quantity=1)
        self.assertEqual(len(cart), 0)  # Should not add to cart

        # Test unavailable product
        self.nysc_tour.available = False
        self.nysc_tour.save()

        cart.add(product=self.nysc_tour, quantity=1)
        self.assertEqual(len(cart), 0)  # Should not add to cart
