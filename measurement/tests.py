from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Measurement

User = get_user_model()


class MeasurementModelTest(TestCase):
    """Test cases for the Measurement model."""

    def setUp(self):
        """Set up test users and measurements."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.measurement = Measurement.objects.create(
            user=self.user,
            chest=Decimal("40.00"),
            waist=Decimal("32.00"),
            hips=Decimal("38.00"),
        )

    def test_measurement_creation(self):
        """Test that a measurement can be created successfully."""
        self.assertIsNotNone(self.measurement.id)
        self.assertEqual(self.measurement.user, self.user)
        self.assertEqual(self.measurement.chest, Decimal("40.00"))

    def test_string_representation(self):
        """Test the string representation of a measurement."""
        expected = f"Measurements for {self.user.username} ({self.measurement.created_at.date()})"
        self.assertEqual(str(self.measurement), expected)

    def test_uuid_generation(self):
        """Test that UUID is auto-generated."""
        self.assertIsNotNone(self.measurement.id)
        self.assertEqual(len(str(self.measurement.id)), 36)  # UUID format

    def test_ordering_by_created_at(self):
        """Test that measurements are ordered by created_at descending."""
        measurement2 = Measurement.objects.create(
            user=self.user, chest=Decimal("42.00")
        )
        measurements = Measurement.objects.all()
        self.assertEqual(measurements[0], measurement2)
        self.assertEqual(measurements[1], self.measurement)

    def test_user_cascade_deletion(self):
        """Test that measurements are deleted when user is deleted."""
        user_id = self.user.id
        measurement_count = Measurement.objects.filter(user=self.user).count()
        self.assertEqual(measurement_count, 1)

        self.user.delete()

        # Check that hard-deleted user also hard-deletes measurements
        # Note: This will only work if soft delete is properly handled
        remaining_measurements = Measurement.objects.all_with_deleted().filter(
            user_id=user_id
        )
        self.assertEqual(remaining_measurements.count(), 0)

    def test_all_fields_nullable(self):
        """Test that all measurement fields accept null values."""
        measurement = Measurement.objects.create(user=self.user)
        self.assertIsNone(measurement.chest)
        self.assertIsNone(measurement.waist)
        self.assertIsNone(measurement.hips)

    def test_min_value_validation(self):
        """Test min value validators on measurement fields."""
        measurement = Measurement(user=self.user, chest=Decimal("10.00"))  # Too small
        with self.assertRaises(ValidationError):
            measurement.full_clean()

    def test_max_value_validation(self):
        """Test max value validators on measurement fields."""
        measurement = Measurement(user=self.user, chest=Decimal("80.00"))  # Too large
        with self.assertRaises(ValidationError):
            measurement.full_clean()

    def test_clean_method_requires_at_least_one_measurement(self):
        """Test that clean method requires at least one measurement field."""
        measurement = Measurement(user=self.user)
        with self.assertRaises(ValidationError) as context:
            measurement.clean()
        self.assertIn("At least one measurement", str(context.exception))

    def test_soft_delete(self):
        """Test that delete() performs soft delete."""
        self.assertFalse(self.measurement.is_deleted)
        self.measurement.delete()

        # Check that it's marked as deleted
        self.assertTrue(self.measurement.is_deleted)

        # Check that it doesn't appear in default queryset
        measurements = Measurement.objects.filter(user=self.user)
        self.assertEqual(measurements.count(), 0)

        # Check that it appears in all_with_deleted queryset
        all_measurements = Measurement.objects.all_with_deleted().filter(
            user=self.user
        )
        self.assertEqual(all_measurements.count(), 1)

    def test_hard_delete(self):
        """Test that hard_delete() permanently removes the measurement."""
        measurement_id = self.measurement.id
        self.measurement.hard_delete()

        # Check that it's completely gone
        all_measurements = Measurement.objects.all_with_deleted().filter(id=measurement_id)
        self.assertEqual(all_measurements.count(), 0)


class MeasurementAPITest(APITestCase):
    """Test cases for the Measurement API endpoints."""

    def setUp(self):
        """Set up test users and authenticate."""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="pass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="pass123"
        )

        self.measurement1 = Measurement.objects.create(
            user=self.user1, chest=Decimal("40.00"), waist=Decimal("32.00")
        )
        self.measurement2 = Measurement.objects.create(
            user=self.user2, chest=Decimal("38.00"), waist=Decimal("30.00")
        )

        self.list_url = "/api/measurement/measurements/"

    def test_list_measurements_requires_authentication(self):
        """Test that listing measurements requires authentication."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_measurements_authenticated(self):
        """Test that authenticated users can list their own measurements."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            str(response.data["results"][0]["id"]), str(self.measurement1.id)
        )

    def test_user_isolation(self):
        """Test that users can only access their own measurements."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        # Ensure user1 can't see user2's measurements
        measurement_ids = [m["id"] for m in response.data["results"]]
        self.assertNotIn(str(self.measurement2.id), measurement_ids)

    def test_create_measurement_valid_data(self):
        """Test creating a measurement with valid data."""
        self.client.force_authenticate(user=self.user1)
        data = {
            "chest": "42.50",
            "waist": "34.00",
            "hips": "40.00",
        }
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Measurement.objects.filter(user=self.user1).count(), 2)

    def test_create_measurement_invalid_data(self):
        """Test creating a measurement with out-of-range values."""
        self.client.force_authenticate(user=self.user1)
        data = {
            "chest": "10.00",  # Below minimum
        }
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("chest", response.data)

    def test_create_measurement_no_measurements(self):
        """Test that creating a measurement without any values fails."""
        self.client.force_authenticate(user=self.user1)
        data = {}
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("At least one measurement", str(response.data))

    def test_retrieve_measurement(self):
        """Test retrieving a specific measurement."""
        self.client.force_authenticate(user=self.user1)
        url = f"{self.list_url}{self.measurement1.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["id"]), str(self.measurement1.id))

    def test_retrieve_other_users_measurement_fails(self):
        """Test that users cannot retrieve other users' measurements."""
        self.client.force_authenticate(user=self.user1)
        url = f"{self.list_url}{self.measurement2.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_measurement(self):
        """Test updating a measurement with PATCH."""
        self.client.force_authenticate(user=self.user1)
        url = f"{self.list_url}{self.measurement1.id}/"
        data = {"chest": "41.00"}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.measurement1.refresh_from_db()
        self.assertEqual(self.measurement1.chest, Decimal("41.00"))

    def test_delete_measurement(self):
        """Test deleting a measurement (soft delete)."""
        self.client.force_authenticate(user=self.user1)
        url = f"{self.list_url}{self.measurement1.id}/"
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify soft delete
        self.measurement1.refresh_from_db()
        self.assertTrue(self.measurement1.is_deleted)

        # Verify it doesn't appear in list
        response = self.client.get(self.list_url)
        self.assertEqual(response.data["count"], 0)

    def test_pagination(self):
        """Test that pagination works correctly."""
        self.client.force_authenticate(user=self.user1)

        # Create 25 measurements (already have 1)
        for i in range(24):
            Measurement.objects.create(user=self.user1, chest=Decimal("40.00"))

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 20)  # Default page size
        self.assertIsNotNone(response.data["next"])

    def test_filtering_by_date(self):
        """Test filtering measurements by created_at."""
        self.client.force_authenticate(user=self.user1)
        created_date = self.measurement1.created_at.date()

        response = self.client.get(f"{self.list_url}?created_at={created_date}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MeasurementSerializerTest(APITestCase):
    """Test cases for the MeasurementSerializer."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.list_url = "/api/measurement/measurements/"

    def test_user_auto_assigned_on_create(self):
        """Test that user is automatically assigned on create."""
        self.client.force_authenticate(user=self.user)
        data = {"chest": "40.00"}
        response = self.client.post(self.list_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        measurement = Measurement.objects.get(id=response.data["id"])
        self.assertEqual(measurement.user, self.user)

    def test_read_only_fields(self):
        """Test that user, created_at, updated_at, is_deleted are read-only."""
        self.client.force_authenticate(user=self.user)
        measurement = Measurement.objects.create(user=self.user, chest=Decimal("40.00"))

        url = f"{self.list_url}{measurement.id}/"
        data = {
            "chest": "41.00",
            "user": 9999,  # Try to change user
            "is_deleted": True,  # Try to set deleted flag
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        measurement.refresh_from_db()
        self.assertEqual(measurement.user, self.user)  # User unchanged
        self.assertFalse(measurement.is_deleted)  # is_deleted unchanged
        self.assertEqual(measurement.chest, Decimal("41.00"))  # chest updated

    def test_user_cannot_be_changed_on_update(self):
        """Test that user field cannot be modified through API."""
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="pass123"
        )
        self.client.force_authenticate(user=self.user)

        measurement = Measurement.objects.create(user=self.user, chest=Decimal("40.00"))
        url = f"{self.list_url}{measurement.id}/"

        data = {"user": other_user.id, "chest": "42.00"}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        measurement.refresh_from_db()
        self.assertEqual(measurement.user, self.user)  # User unchanged


class MeasurementIntegrationTest(TestCase):
    """Integration tests for measurement retrieval in other apps."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_most_recent_measurement_retrieval(self):
        """Test that most recent measurement is retrieved correctly."""
        # Create measurements at different times
        measurement1 = Measurement.objects.create(
            user=self.user, chest=Decimal("40.00")
        )
        measurement2 = Measurement.objects.create(
            user=self.user, chest=Decimal("42.00")
        )
        measurement3 = Measurement.objects.create(
            user=self.user, chest=Decimal("44.00")
        )

        # Retrieve most recent measurement (same as orderitem_generation does)
        latest = (
            Measurement.objects.select_related("user")
            .filter(user=self.user)
            .order_by("-created_at")
            .first()
        )

        self.assertEqual(latest, measurement3)
        self.assertEqual(latest.chest, Decimal("44.00"))
