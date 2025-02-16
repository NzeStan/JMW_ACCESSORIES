# cart/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.apps import apps
from django.contrib import messages
from .cart import Cart
from .forms import CartAddProductForm
from django.http import HttpResponse
from django.http import JsonResponse


@require_POST
def cart_add(request, product_type, product_id):
    """Add a product to cart with proper message handling."""
    if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "error"}, status=400)
    cart = Cart(request)

    try:
        # Clear existing messages
        storage = messages.get_messages(request)
        for _ in storage:
            pass  # Iterate through to mark all messages as used
        storage.used = True

        model = apps.get_model("products", Cart.MODEL_MAPPING[product_type])
        product = get_object_or_404(model, id=product_id)

        if not product.can_be_purchased:
            messages.error(request, "This product is not available for purchase.")
            return JsonResponse(
                {"status": "error", "reason": "not_purchasable"}, status=400
            )

        form = CartAddProductForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please check your input and try again.")
            return JsonResponse(
                {"status": "error", "reason": "form_invalid", "errors": form.errors},
                status=400,
            )

        cd = form.cleaned_data
        extra_fields = {}

        # Handle product-specific requirements
        handlers = {
            "nysc_kit": _handle_nysc_kit_fields,
            "nysc_tour": _handle_nysc_tour_fields,
            "church": _handle_church_fields,
        }

        handler = handlers.get(product_type)
        if handler:
            if product_type == "nysc_kit":
                if not handler(request, product, extra_fields):
                    return JsonResponse(
                        {"status": "error", "reason": "validation_failed"}, status=400
                    )
            else:
                if not handler(request, extra_fields):
                    return JsonResponse(
                        {"status": "error", "reason": "validation_failed"}, status=400
                    )

        cart.add(
            product=product,
            quantity=cd["quantity"],
            override_quantity=cd["override"],
            **extra_fields,
        )

        messages.success(request, f"{product.name} added to cart successfully")
        return JsonResponse(
            {
                "status": "success",
                "cartCount": len(cart),
            }
        )

    except Exception as e:
        messages.error(request, "Error adding item to cart.")
        return JsonResponse(
            {"status": "error", "reason": "unexpected_error"}, status=400
        )


def _handle_nysc_kit_fields(request, product, extra_fields):
    """
    Handle NYSC Kit specific requirements.
    Sets appropriate size based on product type.
    Returns False if validation fails.
    """
    if product.type == "kakhi":
        extra_fields["size"] = "Measurement"
    elif product.type == "cap":
        extra_fields["size"] = "Free Size"
    elif product.type == "vest":
        size = request.POST.get("size")
        if not size:
            messages.error(request, "Please select a size for the vest.")
            return False
        extra_fields["size"] = size
    return True


def _handle_nysc_tour_fields(request, extra_fields):
    """
    Handle NYSC Tour specific requirements.
    Validates and processes call-up number.
    Returns False if validation fails.
    """
    call_up = request.POST.get("call_up_number", "").strip().upper()
    if not call_up:
        messages.error(request, "Please enter your NYSC Call-up Number.")
        return False
    extra_fields["call_up_number"] = call_up
    return True


def _handle_church_fields(request, extra_fields):
    """
    Handle Church merchandise specific requirements.
    Validates size and processes custom name if present.
    Returns False if validation fails.
    """
    size = request.POST.get("size")
    if not size:
        messages.error(request, "Please select a size.")
        return False
    extra_fields["size"] = size

    if request.POST.get("custom_name") == "true":
        custom_name_text = request.POST.get("custom_name_text", "").strip()
        if not custom_name_text:
            messages.error(
                request, "Please enter a custom name or uncheck the custom name option."
            )
            return False
        extra_fields["custom_name_text"] = custom_name_text
    return True


@require_POST
def cart_remove(request, product_type, product_id):
    """
    Remove an item from the cart, ensuring proper message handling.
    We use redirect to ensure messages are processed through Django's standard flow.
    """
    cart = Cart(request)

    try:
        model = apps.get_model("products", Cart.MODEL_MAPPING[product_type])
        product = get_object_or_404(model, id=product_id)
        cart.remove(product)
        messages.success(request, f"{product.name} removed from cart.")

    except LookupError:
        messages.error(request, "Invalid product type.")

    # Always redirect to ensure proper message handling
    return redirect("cart:cart_detail")


@require_POST
def update_quantity(request, product_type, product_id):
    cart = Cart(request)

    try:
        model = apps.get_model("products", Cart.MODEL_MAPPING[product_type])
        product = get_object_or_404(model, id=product_id)

        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity < 1:
                raise ValueError
        except ValueError:
            messages.error(request, "Please enter a valid quantity.")
            return HttpResponse(status=400)

        # Find the existing item to preserve its extra fields
        existing_item = None
        for item in cart:
            if (
                item["product"].id == product_id
                and item["product"].product_type == product_type
            ):
                existing_item = item
                break

        if existing_item:
            cart.add(
                product=product,
                quantity=quantity,
                override_quantity=True,
                **existing_item.get("extra_fields", {}),
            )
            messages.success(request, "Cart updated successfully.")

        # The key change: Instead of rendering the template,
        # we'll redirect to ensure clean message handling
        return redirect("cart:cart_detail")

    except Exception as e:
        messages.error(request, "Error updating cart.")
        return redirect("cart:cart_detail")


@require_POST  # Only allow POST requests for this action
def cart_clear(request):
    """Clear all items from the cart."""
    cart = Cart(request)
    cart.clear()
    messages.success(request, "Your cart has been cleared.")
    return redirect("cart:cart_detail")


def cart_detail(request):
    """
    Display cart contents and provide forms for quantity updates.
    Adds an update form to each cart item.
    """
    cart = Cart(request)
    for item in cart:
        item["update_quantity_form"] = CartAddProductForm(
            initial={"quantity": item["quantity"], "override": True}
        )
    return render(request, "cart/detail.html", {"cart": cart})


def cart_summary(request):
    """
    Return the cart summary for HTMX updates.
    This view renders just the cart summary component, which includes
    the total items and total price.
    """
    cart = Cart(request)
    return render(request, "cart/includes/cart_summary.html", {"cart": cart})
