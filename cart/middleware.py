# cart/middleware.py
from django.contrib import messages
from .cart import Cart
from django.apps import apps


class CartCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

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

    def __call__(self, request):
        # Only process if there's a session and cart
        if hasattr(request, "session") and "cart" in request.session:
            cart = Cart(request)
            removed_items = cart.cleanup()

            # If items were removed, add a message
            if removed_items:
                message_parts = []
                if removed_items.get("deleted"):
                    message_parts.append(
                        f"{len(removed_items['deleted'])} item(s) were removed because they are no longer available"
                    )
                if removed_items.get("out_of_stock"):
                    message_parts.append(
                        f"{len(removed_items['out_of_stock'])} item(s) were removed because they are out of stock"
                    )

                if message_parts:
                    messages.warning(
                        request,
                        "Your cart has been updated: "
                        + " and ".join(message_parts)
                        + ".",
                    )

        response = self.get_response(request)
        return response
