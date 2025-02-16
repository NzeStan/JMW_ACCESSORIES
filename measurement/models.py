from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


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

    # Timestamp fields
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When these measurements were first recorded"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When these measurements were last updated"
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

    def __str__(self):
        """Return a string representation of the measurement."""
        return f"Measurements for {self.user.username} ({self.created_at.date()})"

    def get_absolute_url(self):
        """Return the URL to access a detail view of this measurement."""
        return reverse("update_measurement", args=[str(self.id)])

