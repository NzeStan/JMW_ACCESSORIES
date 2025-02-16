from django.db import models
import uuid


class PaymentTransaction(models.Model):
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.EmailField()
    status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed")],
        default="pending",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    orders = models.ManyToManyField("order.BaseOrder", related_name="payments")
    metadata = models.JSONField(default=dict, blank=True)

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

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"JMW-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created"]
