import uuid
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from .validators import validate_phone_number

class Order(models.Model):
    """Unified Order model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Contact Info
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone_number = models.CharField(
        max_length=11,
        validators=[validate_phone_number],
        help_text="Enter an 11-digit phone number",
    )
    
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

    def __str__(self):
        return f"Order {self.id}"

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

    def get_cost(self):
        return self.price * self.quantity
