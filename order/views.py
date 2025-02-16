# views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .forms import BaseOrderForm, NyscKitOrderForm, ChurchOrderForm, NyscTourOrderForm
from .models import BaseOrder, NyscKitOrder, ChurchOrder, NyscTourOrder, OrderItem
from django.views.decorators.csrf import ensure_csrf_cookie
from cart.cart import Cart
from django.http import HttpResponse

# Dictionary mapping model names to their respective forms and order models
ORDER_TYPES = {
    "NyscKit": {"form": NyscKitOrderForm, "model": NyscKitOrder},
    "Church": {"form": ChurchOrderForm, "model": ChurchOrder},
    "NyscTour": {"form": NyscTourOrderForm, "model": NyscTourOrder},
}


@login_required
def checkout(request):
    cart = Cart(request)
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    # Group cart items by product type
    grouped_items = {}
    for item in cart:
        product_type = item["product"].__class__.__name__
        if product_type not in grouped_items:
            grouped_items[product_type] = []
        grouped_items[product_type].append(item)

    if request.method == "POST":
        try:
            print("Processing POST request...")  # Debug
            base_form = BaseOrderForm(request.POST)
            order_forms = {}

            # Print form data for debugging
            print("POST data:", request.POST)

            for product_type in grouped_items.keys():
                if product_type in ORDER_TYPES:
                    order_forms[product_type] = ORDER_TYPES[product_type]["form"](
                        request.POST
                    )

            # Check form validation
            forms_valid = base_form.is_valid()
            if not forms_valid:
                print("Base form errors:", base_form.errors)  # Debug

            forms_valid = forms_valid and all(
                form.is_valid() for form in order_forms.values()
            )

            # Print any form errors
            for product_type, form in order_forms.items():
                if not form.is_valid():
                    print(f"{product_type} form errors:", form.errors)  # Debug

            if forms_valid:
                print("Forms are valid, processing orders...")  # Debug
                try:
                    with transaction.atomic():
                        orders_created = []

                        for product_type, items in grouped_items.items():
                            if product_type in ORDER_TYPES:
                                # Get the cleaned data from base form
                                order_data = {
                                    "user": request.user,
                                    "email": request.user.email,
                                    "first_name": base_form.cleaned_data["first_name"],
                                    "middle_name": base_form.cleaned_data[
                                        "middle_name"
                                    ],
                                    "last_name": base_form.cleaned_data["last_name"],
                                    "phone_number": base_form.cleaned_data[
                                        "phone_number"
                                    ],
                                }

                                # Add specific form data for this order type
                                order_data.update(
                                    order_forms[product_type].cleaned_data
                                )

                                # Create the order instance
                                order = ORDER_TYPES[product_type]["model"](**order_data)
                                order.save()
                                orders_created.append((order, items))

                        # Create order items
                        for order, items in orders_created:
                            for item in items:
                                OrderItem.objects.create(
                                    order=order,
                                    content_type=ContentType.objects.get_for_model(
                                        item["product"]
                                    ),
                                    object_id=item["product"].id,
                                    price=item["price"],
                                    quantity=item["quantity"],
                                    extra_fields=item["extra_fields"],
                                )

                            order.total_cost = sum(
                                item.get_cost() for item in order.items.all()
                            )
                            order.save()

                        # Store order IDs in session
                        request.session["pending_orders"] = [
                            order.id for order, _ in orders_created
                        ]
            
                        # Store order IDs in session (convert UUID to string)
                    request.session["pending_orders"] = [
                        str(order.id) for order, _ in orders_created
                    ]

                    # Clear cart and redirect
                    cart.clear()
                    return redirect("payment:initiate")

                except Exception as e:
                    messages.error(
                        request, "An error occurred while processing your order."
                    )
                    raise  # Re-raise to see full traceback in development

            else:
                messages.error(request, "Please correct the errors in the form.")

        except Exception as e:
            messages.error(request, "An unexpected error occurred. Please try again.")

    # GET request or form invalid
    base_form = BaseOrderForm(
        initial=(
            {
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
            }
            if request.method == "GET"
            else None
        ),
        data=request.POST if request.method == "POST" else None,
    )

    order_forms = {
        product_type: ORDER_TYPES[product_type]["form"](
            data=request.POST if request.method == "POST" else None
        )
        for product_type in grouped_items.keys()
        if product_type in ORDER_TYPES
    }

    context = {
        "base_form": base_form,
        "order_forms": order_forms,
        "cart": cart,
        "grouped_items": grouped_items,
    }

    return render(request, "order/checkout.html", context)
