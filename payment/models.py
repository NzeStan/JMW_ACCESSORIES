from django.db import models
from django.conf import settings
import uuid
import random
import string

class PaymentTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=100, unique=True, editable=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.EmailField()
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed")],
        default="pending",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # Primary order reference (single order per payment)
    order = models.ForeignKey(
        "order.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions"
    )

    # Legacy support for multiple orders (keep for backwards compatibility)
    orders = models.ManyToManyField("order.Order", related_name="payments", blank=True)

    # Paystack specific fields
    paystack_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Paystack transaction reference")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when payment was verified")

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=['reference'], name='payment_reference_idx'),
            models.Index(fields=['paystack_reference'], name='payment_paystack_ref_idx'),
            models.Index(fields=['email'], name='payment_email_idx'),
            models.Index(fields=['status', '-created'], name='payment_status_created_idx'),
            models.Index(fields=['-created'], name='payment_created_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            prefix = settings.COMPANY_SHORT_NAME if hasattr(settings, 'COMPANY_SHORT_NAME') else 'JMW'
            random_part = ''.join(random.choices(string.digits + string.ascii_uppercase, k=8))
            self.reference = f"{prefix}-PAY-{random_part}"

            # Ensure uniqueness
            while PaymentTransaction.objects.filter(reference=self.reference).exists():
                random_part = ''.join(random.choices(string.digits + string.ascii_uppercase, k=8))
                self.reference = f"{prefix}-PAY-{random_part}"

        super().save(*args, **kwargs)

    def get_formatted_metadata(self):
        """Returns formatted metadata for display"""
        if not self.metadata:
            return "No metadata"
        return {
            "Orders": [order_id for order_id in self.metadata.get("orders", [])],
            "Customer": self.metadata.get("customer_name", "N/A"),
        }

    def __str__(self):
        return f"Payment {self.reference} - {self.status}"
