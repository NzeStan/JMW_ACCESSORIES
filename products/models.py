from django.db import models
from django.urls import reverse
import uuid
from cloudinary_storage.storage import MediaCloudinaryStorage
from django.core.validators import MinValueValidator, URLValidator
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.text import slugify
from django.db.models import Case, When
from .constants import (
    NYSC_KIT_TYPE_CHOICES,
    PRODUCT_TYPE_CHOICES,
    CHURCH_CHOICES,
    STATES,
    CHURCH_PRODUCT_NAME,
    NYSC_KIT_PRODUCT_NAME,
    CATEGORY_NAME_CHOICES,
)
from django.db.models import Avg


class SoftDeleteQuerySet(QuerySet):
    """QuerySet that implements soft delete functionality."""

    def delete(self):
        """Soft delete all objects in the queryset"""
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        """Permanently delete objects"""
        return super().delete()

    def alive(self):
        """Return only non-deleted objects"""
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        """Return only deleted objects"""
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """Manager that implements soft delete functionality."""

    def get_queryset(self):
        # ✅ Fixed: Filter out soft-deleted items by default
        return SoftDeleteQuerySet(self.model, using=self._db).alive()

    def alive(self):
        return self.get_queryset().alive()

    def dead(self):
        # ✅ Need to bypass the alive() filter to get dead items
        return SoftDeleteQuerySet(self.model, using=self._db).dead()
    
    def all_with_deleted(self):
        """Return all objects including soft-deleted ones"""
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    """Abstract base model implementing soft delete."""

    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    def delete(self, hard=False):
        if hard:
            return super().delete()
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.deleted_at = None
        self.save()


def validate_image_url(value):
    """Validates that a URL points to an image file."""
    url_validator = URLValidator()
    try:
        url_validator(value)
        valid_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        if not any(ext in value.lower() for ext in valid_extensions):
            raise ValidationError("URL must point to an image file")
    except ValidationError:
        raise ValidationError("Enter a valid image URL")


class Category(SoftDeleteModel):
    """Model for product categories."""

    name = models.CharField(max_length=200, choices=CATEGORY_NAME_CHOICES)
    slug = models.SlugField(max_length=200, unique=True)
    product_type = models.CharField(max_length=50, choices=PRODUCT_TYPE_CHOICES)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["product_type"]),
        ]
        verbose_name = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:product_list_by_category", args=[self.slug])


class ProductQuerySet(QuerySet):
    """Custom QuerySet for product filtering."""

    def available(self):
        """Return only available products"""
        return self.filter(available=True, out_of_stock=False)

    def out_of_stock(self):
        """Return out of stock products"""
        return self.filter(out_of_stock=True)

    def by_category(self, category_slug):
        """Filter products by category slug"""
        return self.filter(category__slug=category_slug)

    def search(self, query):
        """Basic search functionality"""
        return self.filter(
            models.Q(name__icontains=query) | models.Q(description__icontains=query)
        )


class ProductManager(models.Manager):
    """Manager for product-specific operations."""

    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)

    def available(self):
        return self.get_queryset().available()

    def out_of_stock(self):
        return self.get_queryset().out_of_stock()

    def by_category(self, category_slug):
        return self.get_queryset().by_category(category_slug)

    def search(self, query):
        return self.get_queryset().search(query)


class BaseProduct(models.Model):
    """Abstract base class for all product types."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category, related_name="%(class)ss", on_delete=models.SET_NULL, null=True
    )
    # FIXED: Added Cloudinary storage to all image fields
    image = models.ImageField(
        upload_to="product_images/", 
        storage=MediaCloudinaryStorage(),
        blank=True
    )
    image_1 = models.ImageField(
        upload_to="product_images/", 
        storage=MediaCloudinaryStorage(),
        blank=True
    )
    image_2 = models.ImageField(
        upload_to="product_images/", 
        storage=MediaCloudinaryStorage(),
        blank=True
    )
    image_3 = models.ImageField(
        upload_to="product_images/", 
        storage=MediaCloudinaryStorage(),
        blank=True
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    available = models.BooleanField(
        default=True, help_text="Controls whether the product is visible on the site"
    )
    out_of_stock = models.BooleanField(
        default=False, help_text="Controls whether the product can be purchased"
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ProductManager()

    class Meta:
        abstract = True
        ordering = ["id"]

    @property
    def can_be_purchased(self):
        """Determines if a product can be purchased."""
        return self.available and not self.out_of_stock

    @property
    def display_status(self):
        """Returns product status information for UI display."""
        if not self.available:
            return {
                "text": "Not Available",
                "badge_class": "badge badge-ghost",
                "icon": "x-circle",
            }
        if self.out_of_stock:
            return {
                "text": "Out of Stock",
                "badge_class": "badge badge-warning",
                "icon": "alert-circle",
            }
        return {
            "text": "Available",
            "badge_class": "badge badge-success",
            "icon": "check-circle",
        }

class NyscKit(BaseProduct):
    """NYSC Kit specific model with specialized size handling."""

    name = models.CharField(
        max_length=100, choices=NYSC_KIT_PRODUCT_NAME, verbose_name="Product Name"
    )
    slug = models.SlugField(max_length=200)
    type = models.CharField(
        max_length=20,
        choices=NYSC_KIT_TYPE_CHOICES,
        help_text="Select the type of NYSC Kit product",
    )

    class Meta(BaseProduct.Meta):
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["type"]),
        ]
        verbose_name = "nysckit"
        verbose_name_plural = "nysckits"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Handles slug generation."""
        if not self.slug:
            self.slug = slugify(self.name)
            if NyscKit.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    class Meta:
        ordering = [
            Case(
                When(type="kakhi", then=0),
                When(type="vest", then=2),
                When(type="cap", then=1),
                default=3,
            ),
            "type",
        ]

    product_type = "nysc_kit"

    def get_absolute_url(self):
        return reverse(
            "products:product_detail", args=[self.product_type, self.id, self.slug]
        )


class NyscTour(BaseProduct):
    """NYSC Tour specific model."""

    name = models.CharField(
        max_length=100, choices=STATES, verbose_name="Product Name"
    )
    slug = models.SlugField(max_length=200)

    class Meta(BaseProduct.Meta):
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
        ]
        verbose_name = "nysctour"
        verbose_name_plural = "nysctours"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Handles slug generation."""
        if not self.slug:
            self.slug = slugify(self.name)
            if NyscTour.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    product_type = "nysc_tour"

    def get_absolute_url(self):
        return reverse(
            "products:product_detail", args=[self.product_type, self.id, self.slug]
        )


class Church(BaseProduct):
    """Church specific model."""

    name = models.CharField(
        max_length=100, choices=CHURCH_PRODUCT_NAME, verbose_name="Product Name"
    )
    slug = models.SlugField(max_length=200)
    church = models.CharField(max_length=50, choices=CHURCH_CHOICES)

    class Meta(BaseProduct.Meta):
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["church"]),
        ]
        verbose_name = "church"
        verbose_name_plural = "churchies"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Handles slug generation."""
        if not self.slug:
            self.slug = slugify(self.name)
            if Church.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    product_type = "church"

    def get_absolute_url(self):
        return reverse(
            "products:product_detail", args=[self.product_type, self.id, self.slug]
        )