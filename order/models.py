import uuid
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from  . validators import validate_phone_number, validate_state_code


class BaseOrder(models.Model):
    """Base model for all order types"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    serial_number = models.PositiveIntegerField(
        unique=True, editable=False, db_index=True
    )
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone_number = models.CharField(
        max_length=11,
        validators=[validate_phone_number],
        help_text="Enter an 11-digit phone number",
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-created"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super(BaseOrder, self).__init__(*args, **kwargs)
        if user:
            self.email = user.email

    def save(self, *args, **kwargs):
        if not self.serial_number:
            last_serial = BaseOrder.objects.all().order_by("serial_number").last()
            if last_serial:
                self.serial_number = last_serial.serial_number + 1
            else:
                self.serial_number = 1

        # First save to get the primary key
        super(BaseOrder, self).save(*args, **kwargs)

        # Now update total cost if there are items
        if hasattr(self, "items"):
            self.total_cost = sum(item.get_cost() for item in self.items.all())
            super(BaseOrder, self).save(update_fields=["total_cost"])

    def __str__(self):
        return f"Order #{self.serial_number}"

    def get_total_cost(self):
        if not self.pk:  # If no primary key yet, return 0
            return 0
        return sum(item.get_cost() for item in self.items.all())


class NyscKitOrder(BaseOrder):
    """NYSC Kit specific order model"""

    state_code = models.CharField(max_length=11, validators=[validate_state_code])
    state = models.CharField(max_length=50)
    local_government = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        self.state_code = self.state_code.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "NYSC Kit Order"
        verbose_name_plural = "NYSC Kit Orders"


class NyscTourOrder(BaseOrder):
    """NYSC Tour specific order model"""

    class Meta:
        verbose_name = "NYSC Tour Order"
        verbose_name_plural = "NYSC Tour Orders"


class ChurchOrder(BaseOrder):
    """Church merchandise specific order model"""

    pickup_on_camp = models.BooleanField(default=True)
    delivery_state = models.CharField(max_length=50, blank=True)
    delivery_lga = models.CharField(max_length=100, blank=True)

    def clean(self):
        """Validate delivery details if not picking up on camp"""
        if not self.pickup_on_camp:
            if not self.delivery_state or not self.delivery_lga:
                raise ValidationError(
                    {
                        "delivery_state": "Delivery state is required for non-pickup orders",
                        "delivery_lga": "Delivery LGA is required for non-pickup orders",
                    }
                )

    class Meta:
        verbose_name = "Church Order"
        verbose_name_plural = "Church Orders"


class OrderItem(models.Model):
    order = models.ForeignKey(BaseOrder, related_name="items", on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.UUIDField()
    product = GenericForeignKey("content_type", "object_id")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    quantity = models.PositiveIntegerField(default=1)
    extra_fields = models.JSONField(default=dict, blank=True)

    def get_cost(self):
        return self.price * self.quantity if self.price else 0
