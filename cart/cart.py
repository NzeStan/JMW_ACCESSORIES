# cart/cart.py
from decimal import Decimal
from django.conf import settings
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


class Cart:
    MODEL_MAPPING = {"nysc_kit": "nysckit", "nysc_tour": "nysctour", "church": "church"}

    def validate_product(self, product_type, product_id):
        """
        Check if a product exists and is available for purchase.
        Returns (exists, available, message) tuple.
        """
        try:
            model = apps.get_model("products", self.MODEL_MAPPING[product_type])
            product = model.objects.get(id=product_id)
            if not product.available:
                return True, False, "no longer available"
            if product.out_of_stock:
                return True, False, "out of stock"
            return True, True, None
        except (model.DoesNotExist, LookupError):
            return False, False, "no longer exists"

    @staticmethod
    def get_clothes_sizes():
        return [
            ("S", "Small"),
            ("M", "Medium"),
            ("L", "Large"),
            ("XL", "Extra Large"),
            ("XXL", "2X Large"),
            ("XXXL", "3X Large"),
            ("XXXXL", "4X Large"),
        ]

    def __init__(self, request):
        """Initialize the cart."""
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def __iter__(self):
        """Iterate over items in cart and get the products from the database."""
        for item_key in self.cart.keys():
            try:
                # Split our composite key to get product info
                key_parts = item_key.split("|||")
                product_info = key_parts[0]
                product_type, product_id = product_info.split(":::")

                # Get the correct model and fetch the product
                model_name = self.MODEL_MAPPING[product_type]
                model = apps.get_model("products", model_name)
                product = model.objects.get(id=product_id)

                # Create a copy of the cart item data
                item = self.cart[item_key].copy()

                # Add the product object to the item
                item['product'] = product

                # Convert price to Decimal for calculations
                item['price'] = Decimal(item['price'])
                item['total_price'] = item['price'] * item['quantity']

                yield item

            except (ValueError, KeyError, LookupError) as e:
                logger.error(f"Error processing cart item: {e}")
                continue

    def generate_item_key(self, product, extra_fields):
        """Generate a unique key for cart items that includes product variations."""
        key_parts = [f"{product.product_type}:::{product.id}"]

        if extra_fields:
            # Sort the keys to ensure consistent ordering
            sorted_fields = sorted(extra_fields.items())
            key_parts.extend(f"{k}:::{v}" for k, v in sorted_fields)

        key = "|||".join(key_parts)
        logger.debug(f"Generated cart key: {key}")
        return key

    def add(self, product, quantity=1, override_quantity=False, **extra_fields):
        """Add a product to cart with variation handling."""
        if not product.can_be_purchased:
            logger.warning(f"Attempted to add unavailable product {product.id} to cart")
            return

        # Transform applicable fields to uppercase
        transformed_fields = {}

        # Get the actual extra fields (might be nested in 'extra_fields' key)
        fields_to_transform = extra_fields.get('extra_fields', extra_fields)

        for key, value in fields_to_transform.items():
            if key in ['call_up_number', 'custom_name_text']:
                transformed_fields[key] = str(value).upper() if value else value
            else:
                transformed_fields[key] = value

        item_key = self.generate_item_key(product, transformed_fields)

        if item_key not in self.cart:
            self.cart[item_key] = {
                'quantity': 0,
                'price': str(product.price),
                'extra_fields': transformed_fields  # Store transformed fields
            }

        if override_quantity:
            self.cart[item_key]['quantity'] = quantity
        else:
            self.cart[item_key]['quantity'] += quantity

        self.save()

        logger.debug(f"Added item to cart. Key: {item_key}, Item: {self.cart[item_key]}")

    def remove(self, product, extra_fields=None):
        """
        Remove a specific item from the cart.

        We need to find the exact item using both product info and extra fields,
        since the same product might be in the cart multiple times with different options.
        """
        # Find the matching item key
        for item_key in list(self.cart.keys()):
            key_parts = item_key.split("|||")
            product_info = key_parts[0]
            current_type, current_id = product_info.split(":::")

            # Check if this is the product we want to remove
            if current_type == product.product_type and str(current_id) == str(
                product.id
            ):
                # If extra_fields were provided, check they match
                if extra_fields:
                    item_extra_fields = self.cart[item_key].get("extra_fields", {})
                    if item_extra_fields == extra_fields:
                        del self.cart[item_key]
                        self.save()
                        break
                else:
                    # If no extra_fields provided, just remove the item
                    del self.cart[item_key]
                    self.save()
                    break

    def __len__(self):
        """Count total items in cart."""
        return sum(item["quantity"] for item in self.cart.values())

    def get_total_price(self):
        """Calculate total price of items in cart."""
        return sum(
            Decimal(item["price"]) * item["quantity"] for item in self.cart.values()
        )

    def clear(self):
        """Remove cart from session."""
        # Clear the cart dictionary first
        self.cart = {}
        # Delete the cart key from session
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
        self.save()

    def save(self):
        """Mark session as modified to ensure it's saved."""
        self.session.modified = True

    def cleanup(self):
        """
        Remove invalid items from cart.
        Returns dict with lists of removed items and their reasons.
        """
        removed_items = {"deleted": [], "out_of_stock": []}

        # Create a list of keys to avoid modification during iteration
        cart_keys = list(self.cart.keys())

        for item_key in cart_keys:
            try:
                key_parts = item_key.split("|||")
                product_info = key_parts[0]
                product_type, product_id = product_info.split(":::")

                exists, available, reason = self.validate_product(
                    product_type, product_id
                )

                if not exists or not available:
                    # Store item info before removing
                    item_info = {
                        "product_type": product_type,
                        "product_id": product_id,
                        "quantity": self.cart[item_key]["quantity"],
                    }

                    # Remove the item
                    del self.cart[item_key]

                    # Track removal reason
                    if not exists:
                        removed_items["deleted"].append(item_info)
                    else:
                        removed_items["out_of_stock"].append(item_info)

                    self.save()

            except (ValueError, KeyError) as e:
                # Log invalid cart item
                logger.error(f"Invalid cart item found during cleanup: {e}")
                del self.cart[item_key]
                self.save()

        return removed_items if any(removed_items.values()) else None
