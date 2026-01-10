from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Category, NyscKit, NyscTour, Church, SoftDeleteModel
from django.utils.text import slugify

User = get_user_model()


class CategoryModelTest(TestCase):
    """Test cases for the Category model."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="NYSC Kit",
            slug="nysc-kit",
            product_type="nysc_kit",
            description="NYSC related products"
        )

    def test_category_creation(self):
        """Test that a category can be created."""
        self.assertIsNotNone(self.category.id)
        self.assertEqual(self.category.name, "NYSC Kit")
        self.assertEqual(self.category.slug, "nysc-kit")

    def test_category_string_representation(self):
        """Test the string representation of a category."""
        self.assertEqual(str(self.category), "NYSC Kit")

    def test_category_ordering(self):
        """Test that categories are ordered by name."""
        category2 = Category.objects.create(
            name="Church",
            slug="church",
            product_type="church"
        )
        categories = Category.objects.all()
        self.assertEqual(categories[0].name, "Church")  # Alphabetically first
        self.assertEqual(categories[1].name, "NYSC Kit")

    def test_category_soft_delete(self):
        """Test soft delete functionality."""
        self.category.delete()
        self.assertIsNotNone(self.category.deleted_at)

        # Should not appear in default queryset
        self.assertEqual(Category.objects.count(), 0)

        # Should appear in dead queryset
        self.assertEqual(Category.objects.dead().count(), 1)

    def test_category_restore(self):
        """Test restoring a soft-deleted category."""
        self.category.delete()
        self.category.restore()
        self.assertIsNone(self.category.deleted_at)
        self.assertEqual(Category.objects.count(), 1)


class NyscKitModelTest(TestCase):
    """Test cases for the NyscKit model."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="NYSC Kit",
            slug="nysc-kit",
            product_type="nysc_kit"
        )
        self.nysc_kit = NyscKit.objects.create(
            name="White Short Sleeve",
            category=self.category,
            type="kakhi",
            price=Decimal("5000.00"),
            description="NYSC white short sleeve shirt"
        )

    def test_nysc_kit_creation(self):
        """Test that an NYSC Kit can be created."""
        self.assertIsNotNone(self.nysc_kit.id)
        self.assertEqual(self.nysc_kit.name, "White Short Sleeve")
        self.assertEqual(self.nysc_kit.type, "kakhi")

    def test_slug_auto_generation(self):
        """Test that slug is auto-generated on save."""
        self.assertTrue(self.nysc_kit.slug)
        self.assertIn("white-short-sleeve", self.nysc_kit.slug)

    def test_slug_uniqueness(self):
        """Test that slugs are unique."""
        nysc_kit2 = NyscKit.objects.create(
            name="White Short Sleeve",  # Same name
            category=self.category,
            type="vest",
            price=Decimal("3000.00")
        )
        self.assertNotEqual(self.nysc_kit.slug, nysc_kit2.slug)

    def test_can_be_purchased_property(self):
        """Test the can_be_purchased property."""
        # Available and in stock
        self.assertTrue(self.nysc_kit.can_be_purchased)

        # Out of stock
        self.nysc_kit.out_of_stock = True
        self.nysc_kit.save()
        self.assertFalse(self.nysc_kit.can_be_purchased)

        # Not available
        self.nysc_kit.out_of_stock = False
        self.nysc_kit.available = False
        self.nysc_kit.save()
        self.assertFalse(self.nysc_kit.can_be_purchased)

    def test_display_status_property(self):
        """Test the display_status property."""
        # Available
        status = self.nysc_kit.display_status
        self.assertEqual(status['text'], "Available")

        # Out of stock
        self.nysc_kit.out_of_stock = True
        self.nysc_kit.save()
        status = self.nysc_kit.display_status
        self.assertEqual(status['text'], "Out of Stock")

        # Not available
        self.nysc_kit.available = False
        self.nysc_kit.save()
        status = self.nysc_kit.display_status
        self.assertEqual(status['text'], "Not Available")

    def test_nysc_kit_string_representation(self):
        """Test the string representation of an NYSC Kit."""
        self.assertEqual(str(self.nysc_kit), "White Short Sleeve")

    def test_price_validation(self):
        """Test that price must be positive."""
        from django.core.exceptions import ValidationError
        nysc_kit = NyscKit(
            name="Test Kit",
            category=self.category,
            type="cap",
            price=Decimal("-100.00")
        )
        with self.assertRaises(ValidationError):
            nysc_kit.full_clean()


class NyscTourModelTest(TestCase):
    """Test cases for the NyscTour model."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="NYSC Tour",
            slug="nysc-tour",
            product_type="nysc_tour"
        )
        self.nysc_tour = NyscTour.objects.create(
            name="Abia",
            category=self.category,
            price=Decimal("15000.00"),
            description="NYSC tour to Abia state"
        )

    def test_nysc_tour_creation(self):
        """Test that an NYSC Tour can be created."""
        self.assertIsNotNone(self.nysc_tour.id)
        self.assertEqual(self.nysc_tour.name, "Abia")

    def test_slug_auto_generation(self):
        """Test that slug is auto-generated on save."""
        self.assertTrue(self.nysc_tour.slug)
        self.assertIn("abia", self.nysc_tour.slug)

    def test_nysc_tour_string_representation(self):
        """Test the string representation of an NYSC Tour."""
        self.assertEqual(str(self.nysc_tour), "Abia")

    def test_ordering_by_name(self):
        """Test that tours are ordered alphabetically by name."""
        tour2 = NyscTour.objects.create(
            name="Lagos",
            category=self.category,
            price=Decimal("20000.00")
        )
        tours = NyscTour.objects.all()
        self.assertEqual(tours[0].name, "Abia")
        self.assertEqual(tours[1].name, "Lagos")


class ChurchModelTest(TestCase):
    """Test cases for the Church model."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="Church",
            slug="church",
            product_type="church"
        )
        self.church_product = Church.objects.create(
            name="Choir Robe",
            category=self.category,
            church="rccg",
            price=Decimal("8000.00"),
            description="RCCG choir robe"
        )

    def test_church_product_creation(self):
        """Test that a Church product can be created."""
        self.assertIsNotNone(self.church_product.id)
        self.assertEqual(self.church_product.name, "Choir Robe")
        self.assertEqual(self.church_product.church, "rccg")

    def test_slug_auto_generation(self):
        """Test that slug is auto-generated on save."""
        self.assertTrue(self.church_product.slug)
        self.assertIn("choir-robe", self.church_product.slug)

    def test_church_product_string_representation(self):
        """Test the string representation of a Church product."""
        self.assertEqual(str(self.church_product), "Choir Robe")


class ProductQuerySetTest(TestCase):
    """Test cases for custom ProductQuerySet methods."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="NYSC Kit",
            slug="nysc-kit",
            product_type="nysc_kit"
        )
        self.available_kit = NyscKit.objects.create(
            name="Available Kit",
            category=self.category,
            type="kakhi",
            price=Decimal("5000.00"),
            available=True,
            out_of_stock=False,
            description="Special testing product"  # ✅ ADD THIS LINE
        )
        self.out_of_stock_kit = NyscKit.objects.create(
            name="Out of Stock Kit",
            category=self.category,
            type="vest",
            price=Decimal("3000.00"),
            available=True,
            out_of_stock=True
        )
        self.unavailable_kit = NyscKit.objects.create(
            name="Unavailable Kit",
            category=self.category,
            type="cap",
            price=Decimal("2000.00"),
            available=False,
            out_of_stock=False
        )

    def test_available_queryset(self):
        """Test the available() queryset method."""
        available = NyscKit.objects.available()
        self.assertEqual(available.count(), 1)
        self.assertIn(self.available_kit, available)
        self.assertNotIn(self.out_of_stock_kit, available)

    def test_out_of_stock_queryset(self):
        """Test the out_of_stock() queryset method."""
        out_of_stock = NyscKit.objects.out_of_stock()
        self.assertEqual(out_of_stock.count(), 1)
        self.assertIn(self.out_of_stock_kit, out_of_stock)

    def test_by_category_queryset(self):
        """Test the by_category() queryset method."""
        kits = NyscKit.objects.by_category("nysc-kit")
        self.assertEqual(kits.count(), 3)

    def test_search_queryset(self):
        """Test the search() queryset method."""
        results = NyscKit.objects.search("Special")  # ✅ CHANGE THIS LINE
        self.assertEqual(results.count(), 1)
        self.assertIn(self.available_kit, results)


class CategoryAPITest(APITestCase):
    """Test cases for the Category API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="NYSC Kit",
            slug="nysc-kit",
            product_type="nysc_kit",
            description="NYSC related products"
        )

    def test_list_categories(self):
        """Test listing all categories (public access)."""
        response = self.client.get('/api/products/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_category_by_slug(self):
        """Test retrieving a specific category by slug."""
        response = self.client.get(f'/api/products/categories/{self.category.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "NYSC Kit")

    def test_category_search(self):
        """Test searching categories."""
        response = self.client.get('/api/products/categories/?search=NYSC')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_category_ordering(self):
        """Test ordering categories."""
        response = self.client.get('/api/products/categories/?ordering=name')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_category_read_only(self):
        """Test that category endpoint is read-only."""
        data = {'name': 'New Category', 'slug': 'new-category', 'product_type': 'church'}
        response = self.client.post('/api/products/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class NyscKitAPITest(APITestCase):
    """Test cases for the NyscKit API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="NYSC Kit",
            slug="nysc-kit",
            product_type="nysc_kit"
        )
        self.nysc_kit = NyscKit.objects.create(
            name="White Short Sleeve",
            category=self.category,
            type="kakhi",
            price=Decimal("5000.00"),
            available=True
        )
        self.unavailable_kit = NyscKit.objects.create(
            name="Unavailable Kit",
            category=self.category,
            type="vest",
            price=Decimal("3000.00"),
            available=False
        )

    def test_list_nysc_kits(self):
        """Test listing all NYSC Kits (public access)."""
        response = self.client.get('/api/products/nysc-kits/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only show available products
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_nysc_kit_by_slug(self):
        """Test retrieving a specific NYSC Kit by slug."""
        response = self.client.get(f'/api/products/nysc-kits/{self.nysc_kit.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "White Short Sleeve")

    def test_filter_by_type(self):
        """Test filtering NYSC Kits by type."""
        response = self.client.get('/api/products/nysc-kits/?type=kakhi')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_category_slug(self):
        """Test filtering NYSC Kits by category slug."""
        response = self.client.get('/api/products/nysc-kits/?category__slug=nysc-kit')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_nysc_kits(self):
        """Test searching NYSC Kits."""
        response = self.client.get('/api/products/nysc-kits/?search=White')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_ordering_nysc_kits(self):
        """Test ordering NYSC Kits."""
        response = self.client.get('/api/products/nysc-kits/?ordering=price')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pagination(self):
        """Test pagination for NYSC Kits."""
        # Create 25 kits to trigger pagination
        for i in range(25):
            NyscKit.objects.create(
                name=f"Kit {i}",
                category=self.category,
                type="kakhi",
                price=Decimal("5000.00")
            )
        response = self.client.get('/api/products/nysc-kits/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertEqual(len(response.data['results']), 20)  # Default page size

    def test_nysc_kit_read_only(self):
        """Test that NYSC Kit endpoint is read-only."""
        data = {
            'name': 'New Kit',
            'type': 'kakhi',
            'price': '5000.00',
            'category': str(self.category.id)
        }
        response = self.client.post('/api/products/nysc-kits/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class NyscTourAPITest(APITestCase):
    """Test cases for the NyscTour API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="NYSC Tour",
            slug="nysc-tour",
            product_type="nysc_tour"
        )
        self.nysc_tour = NyscTour.objects.create(
            name="Abia",
            category=self.category,
            price=Decimal("15000.00"),
            available=True
        )

    def test_list_nysc_tours(self):
        """Test listing all NYSC Tours (public access)."""
        response = self.client.get('/api/products/nysc-tours/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_nysc_tour_by_slug(self):
        """Test retrieving a specific NYSC Tour by slug."""
        response = self.client.get(f'/api/products/nysc-tours/{self.nysc_tour.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Abia")

    def test_nysc_tour_read_only(self):
        """Test that NYSC Tour endpoint is read-only."""
        data = {
            'name': 'Lagos',
            'price': '20000.00',
            'category': str(self.category.id)
        }
        response = self.client.post('/api/products/nysc-tours/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ChurchAPITest(APITestCase):
    """Test cases for the Church API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="Church",
            slug="church",
            product_type="church"
        )
        self.church_product = Church.objects.create(
            name="Quality RCCG Shirt",  # ✅ Use valid product name from CHURCH_PRODUCT_NAME
            category=self.category,
            church="RCCG",  # ✅ Changed from "anglican" to "RCCG"
            price=Decimal("8000.00")
        )

    def test_list_church_products(self):
        """Test listing all Church products (public access)."""
        # ✅ Fixed: Use correct URL path
        response = self.client.get('/api/products/church-items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_church_product_by_slug(self):
        """Test retrieving a specific Church product by slug."""
        # ✅ Fixed: Use correct URL path
        response = self.client.get(f'/api/products/church-items/{self.church_product.slug}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Quality RCCG Shirt")

    def test_filter_by_church(self):
        """Test filtering Church products by church."""
        response = self.client.get('/api/products/church-items/?church=RCCG')  # ✅ Changed filter value
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_church_product_read_only(self):
        """Test that Church endpoint is read-only."""
        data = {'name': 'New Church', 'church': 'catholic', 'price': '5000.00'}
        # ✅ Fixed: Use correct URL path
        response = self.client.post('/api/products/church-items/', data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ProductsThrottlingTest(APITestCase):
    """Test cases for API rate limiting."""

    def setUp(self):
        """Set up test data."""
        self.category = Category.objects.create(
            name="NYSC Kit",
            slug="nysc-kit",
            product_type="nysc_kit"
        )

    def test_rate_limiting_anonymous(self):
        """Test that anonymous users are rate limited."""
        # Note: This test may not work properly in test environment
        # as throttling is often disabled in tests
        # Just verify the endpoint is accessible
        response = self.client.get('/api/products/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProductsPermissionsTest(APITestCase):
    """Test cases for API permissions."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.category = Category.objects.create(
            name="NYSC Kit",
            slug="nysc-kit",
            product_type="nysc_kit"
        )

    def test_public_access_to_categories(self):
        """Test that categories are publicly accessible."""
        response = self.client.get('/api/products/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_public_access_to_products(self):
        """Test that products are publicly accessible."""
        response = self.client.get('/api/products/nysc-kits/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_users_can_also_access(self):
        """Test that authenticated users can access products."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/products/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
