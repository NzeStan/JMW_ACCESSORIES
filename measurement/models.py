from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid


class MeasurementManager(models.Manager):
    """Custom manager to handle soft delete functionality."""

    def get_queryset(self):
        """Return only non-deleted measurements by default."""
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        """Return all measurements including soft-deleted ones."""
        return super().get_queryset()


class Measurement(models.Model):
    """
    Stores body measurements for clothing customization.
    All measurements are stored in inches with precision up to 2 decimal places.

    Key features:
    - UUID-based identification for security
    - Comprehensive body measurements for both upper and lower body
    - Validation to ensure measurements fall within realistic ranges
    - Timestamp tracking for measurement history
    """

    # Core fields
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        help_text="User these measurements belong to",
    )
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the measurement set",
    )

    # Custom manager for soft delete
    objects = MeasurementManager()

    # Timestamp fields
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When these measurements were first recorded"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When these measurements were last updated"
    )

    # Soft delete field
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag - marks measurement as deleted without removing from database",
    )

    # Upper body measurements
    chest = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("20.00")),  # Minimum realistic chest size
            MaxValueValidator(Decimal("70.00")),  # Maximum realistic chest size
        ],
        help_text="Chest circumference in inches",
    )

    shoulder = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("12.00")),
            MaxValueValidator(Decimal("30.00")),
        ],
        help_text="Shoulder width in inches",
    )

    neck = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("10.00")),
            MaxValueValidator(Decimal("30.00")),
        ],
        help_text="Neck circumference in inches",
    )

    sleeve_length = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("20.00")),
            MaxValueValidator(Decimal("40.00")),
        ],
        help_text="Length from shoulder to wrist in inches",
    )

    sleeve_round = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("8.00")),
            MaxValueValidator(Decimal("20.00")),
        ],
        help_text="Bicep circumference in inches",
    )

    top_length = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("20.00")),
            MaxValueValidator(Decimal("40.00")),
        ],
        help_text="Length from shoulder to desired shirt bottom in inches",
    )

    # Lower body measurements
    waist = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("20.00")),
            MaxValueValidator(Decimal("60.00")),
        ],
        help_text="Waist circumference in inches",
    )

    thigh = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("12.00")),
            MaxValueValidator(Decimal("40.00")),
        ],
        help_text="Thigh circumference in inches",
    )

    knee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("10.00")),
            MaxValueValidator(Decimal("30.00")),
        ],
        help_text="Knee circumference in inches",
    )

    ankle = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("7.00")),
            MaxValueValidator(Decimal("20.00")),
        ],
        help_text="Ankle circumference in inches",
    )

    hips = models.DecimalField(  # Renamed from 'laps' for clarity
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("25.00")),
            MaxValueValidator(Decimal("70.00")),
        ],
        help_text="Hip circumference in inches",
    )

    trouser_length = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("25.00")),
            MaxValueValidator(Decimal("50.00")),
        ],
        help_text="Length from waist to ankle in inches",
    )


    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Measurement"
        verbose_name_plural = "Measurements"
        indexes = [
            models.Index(
                fields=["user", "-created_at"], name="measurement_user_created_idx"
            ),
        ]

    def __str__(self):
        """Return a string representation of the measurement."""
        return f"Measurements for {self.user.username} ({self.created_at.date()})"

    def get_absolute_url(self):
        """Return the URL to access a detail view of this measurement."""
        return reverse("update_measurement", args=[str(self.id)])

    def clean(self):
        """Ensure at least one measurement field is provided."""
        measurement_fields = [
            self.chest,
            self.shoulder,
            self.neck,
            self.sleeve_length,
            self.sleeve_round,
            self.top_length,
            self.waist,
            self.thigh,
            self.knee,
            self.ankle,
            self.hips,
            self.trouser_length,
        ]

        if all(field is None for field in measurement_fields):
            raise ValidationError("At least one measurement must be provided.")

    def delete(self, *args, **kwargs):
        """Soft delete - mark as deleted instead of removing."""
        self.is_deleted = True
        self.save()

    def hard_delete(self):
        """Permanently delete the measurement."""
        super().delete()

