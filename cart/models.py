from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

import uuid

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.id} ({self.user.email if self.user else 'Anonymous'})"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    
    # Generic relation
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField() # Assuming all products use UUID based on Products app
    content_object = GenericForeignKey('content_type', 'object_id')
    
    quantity = models.PositiveIntegerField(default=1)
    extra_fields = models.JSONField(default=dict, blank=True)
    
    # Optional: Store price at time of addition if needed, or just use property
    
    class Meta:
        unique_together = ('cart', 'content_type', 'object_id')

    def __str__(self):
        return f"{self.quantity} x {self.content_object}"

    @property
    def total_price(self):
        return self.content_object.price * self.quantity
