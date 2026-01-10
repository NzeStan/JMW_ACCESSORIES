import uuid
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from .validators import validate_phone_number

class Order(models.Model):
    """Unified Order model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')

    # Order Reference (unique identifier for customers)
    reference = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        blank=True,
        default='',
        help_text="Unique order reference (e.g., JMW-ORD-123456)"
    )

    # Contact Info
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone_number = models.CharField(
        max_length=11,
        validators=[validate_phone_number],
        help_text="Enter an 11-digit phone number",
    )

    # Shipping Address
    address = models.CharField(max_length=250, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=100, blank=True, default='')

    # Status & Cost
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ])

    # Generic Delivery Details (JSON)
    # can store: state_code, pickup_on_camp, delivery_address, etc.
    delivery_details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=['user', '-created'], name='main_order_user_created_idx'),
            models.Index(fields=['reference'], name='main_order_reference_idx'),
            models.Index(fields=['email'], name='main_order_email_idx'),
            models.Index(fields=['status', 'paid'], name='main_order_status_paid_idx'),
            models.Index(fields=['-created'], name='main_order_created_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            # Generate unique reference on first save
            import random
            import string
            prefix = settings.COMPANY_SHORT_NAME if hasattr(settings, 'COMPANY_SHORT_NAME') else 'ORD'
            random_part = ''.join(random.choices(string.digits, k=6))
            self.reference = f"{prefix}-ORD-{random_part}"

            # Ensure uniqueness
            while Order.objects.filter(reference=self.reference).exists():
                random_part = ''.join(random.choices(string.digits, k=6))
                self.reference = f"{prefix}-ORD-{random_part}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.reference}"

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)

    # Generic relation to Product
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.UUIDField()
    product = GenericForeignKey("content_type", "object_id")

    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    quantity = models.PositiveIntegerField(default=1)

    # Item specific details (e.g. size, color selected)
    extra_fields = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['order'], name='orderitem_order_idx'),
            models.Index(fields=['content_type', 'object_id'], name='orderitem_product_idx'),
        ]

    def get_cost(self):
        """Calculate cost, handling None price gracefully for admin add view"""
        if self.price is None:
            return 0
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product} (Order: {self.order.reference})"