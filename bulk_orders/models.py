# bulk_orders/models.py
from django.db import models
import uuid
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.conf import settings
import logging
from django.urls import reverse
from django.utils import timezone
from django.db import models, transaction
from django.utils.text import slugify
import random
import string

logger = logging.getLogger(__name__)


class BulkOrderLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=300, unique=True, editable=False, help_text="Auto-generated from organization name")
    organization_name = models.CharField(max_length=255)
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)
    custom_branding_enabled = models.BooleanField(default=False)
    payment_deadline = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _generate_unique_slug(self):
        """Generate a unique slug from organization name with random suffix"""
        base_slug = slugify(self.organization_name)
        if len(base_slug) > 280:  # Leave room for suffix
            base_slug = base_slug[:280]
        
        # Generate random 4-character suffix
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        slug = f"{base_slug}-{suffix}"
        
        # Ensure uniqueness
        while BulkOrderLink.objects.filter(slug=slug).exists():
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            slug = f"{base_slug}-{suffix}"
        
        return slug

    def save(self, *args, **kwargs):
        # Generate slug if not set
        if not self.slug:
            self.slug = self._generate_unique_slug()
        
        # Uppercase organization name
        self.organization_name = self.organization_name.upper()
        
        try:
            super().save(*args, **kwargs)
            logger.info(f"BulkOrderLink saved successfully: {self.slug}")
        except Exception as e:
            logger.error(f"Error saving BulkOrderLink: {str(e)}")
            raise

    def get_absolute_url(self):
        # Now uses slug instead of UUID
        return reverse("bulk_orders:order_landing", kwargs={"slug": self.slug})

    def is_expired(self):
        return timezone.now() > self.payment_deadline
    
    def get_shareable_url(self):
        """Returns a clean, shareable URL using the slug"""
        # This would be your frontend URL
        return f"/bulk-order/{self.slug}/"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bulk Order Link"
        verbose_name_plural = "Bulk Order Links"
        indexes = [
            models.Index(
                fields=["created_by", "payment_deadline"],
                name="bulk_order_user_deadline_idx",
            ),
            models.Index(fields=["organization_name"], name="bulk_order_org_name_idx"),
            models.Index(fields=["created_at"], name="bulk_order_created_idx"),
            models.Index(fields=["slug"], name="bulk_order_slug_idx"),
        ]


class CouponCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bulk_order = models.ForeignKey(
        BulkOrderLink, on_delete=models.CASCADE, related_name="coupons"
    )
    code = models.CharField(max_length=20, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
            logger.info(f"CouponCode saved successfully: {self.code}")
        except Exception as e:
            logger.error(f"Error saving CouponCode: {str(e)}")
            raise

    def __str__(self):
        return f"{self.code} ({'Used' if self.is_used else 'Available'})"

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["bulk_order", "is_used"], name="coupon_bulk_order_used_idx"
            ),
            models.Index(fields=["code"], name="coupon_code_idx"),
        ]


class OrderEntry(models.Model):
    SIZE_CHOICES = [
        ("S", "Small"),
        ("M", "Medium"),
        ("L", "Large"),
        ("XL", "Extra Large"),
        ("XXL", "2X Large"),
        ("XXXL", "3X Large"),
        ("XXXXL", "4X Large"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bulk_order = models.ForeignKey(
        BulkOrderLink, on_delete=models.CASCADE, related_name="orders"
    )
    serial_number = models.PositiveIntegerField(editable=False)
    email = models.EmailField()
    full_name = models.CharField(max_length=255)
    size = models.CharField(max_length=10, choices=SIZE_CHOICES)
    custom_name = models.CharField(max_length=255, blank=True)
    coupon_used = models.ForeignKey(
        CouponCode, null=True, blank=True, on_delete=models.SET_NULL
    )
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(OrderEntry, self).__init__(*args, **kwargs)
        if user:
            self.email = user.email

    def save(self, *args, **kwargs):
        if not self.serial_number:
            # Use select_for_update to prevent race conditions
            with transaction.atomic():
                # Lock the related bulk order to prevent concurrent modifications
                bulk_order = BulkOrderLink.objects.select_for_update().get(
                    id=self.bulk_order_id
                )

                # Get the maximum serial number for this bulk order
                max_serial = OrderEntry.objects.filter(
                    bulk_order=self.bulk_order
                ).aggregate(Max("serial_number"))["serial_number__max"]

                self.serial_number = (max_serial or 0) + 1

        self.full_name = self.full_name.upper()
        if self.custom_name:
            self.custom_name = self.custom_name.upper()

        try:
            super().save(*args, **kwargs)
            logger.info(f"OrderEntry saved successfully: {self.id}")
        except Exception as e:
            logger.error(f"Error saving OrderEntry: {str(e)}")
            raise

    def __str__(self):
        return f"#{self.serial_number} - {self.full_name} ({self.bulk_order.organization_name})"

    class Meta:
        ordering = ["bulk_order", "serial_number"]
        verbose_name = "Order Entry"
        verbose_name_plural = "Order Entries"
        unique_together = ["bulk_order", "serial_number"]
        indexes = [
            models.Index(
                fields=["bulk_order", "serial_number"], name="order_bulk_serial_idx"
            ),
            models.Index(fields=["email"], name="order_email_idx"),
            models.Index(fields=["paid"], name="order_paid_idx"),
            models.Index(fields=["size"], name="order_size_idx"),
            models.Index(fields=["created_at"], name="order_created_idx"),
        ]