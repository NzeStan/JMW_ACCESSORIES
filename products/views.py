from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .models import Category, NyscTour, NyscKit, Church
from cart.forms import CartAddProductForm
from django.http import HttpResponse
from cart.cart import Cart
from django.apps import apps
from measurement.models import Measurement
from django.contrib.contenttypes.models import ContentType
from cached.decorators import monitored_cache_page


@monitored_cache_page
def product_list(request, category_slug=None):
    ITEMS_PER_SECTION = 4
    category = None
    categories = Category.objects.all()

    # Get products
    nysc_kits = NyscKit.objects.filter(available=True)
    nysc_tours = NyscTour.objects.filter(available=True)
    churches = Church.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        nysc_kits = nysc_kits.filter(category=category)
        nysc_tours = nysc_tours.filter(category=category)
        churches = churches.filter(category=category)

    context = {
        "category": category,
        "categories": categories,
        "nysc_kits": nysc_kits[:ITEMS_PER_SECTION],
        "nysc_tours": nysc_tours[:ITEMS_PER_SECTION],
        "churches": churches[:ITEMS_PER_SECTION],
        "has_more_kits": nysc_kits.count() > ITEMS_PER_SECTION,
        "has_more_tours": nysc_tours.count() > ITEMS_PER_SECTION,
        "has_more_churches": churches.count() > ITEMS_PER_SECTION,
        "current_page": {"nysc_kit": 1, "nysc_tour": 1, "church": 1},
        # Add cart form for quick add functionality
        "cart_add_form": CartAddProductForm(initial={"quantity": 1}),
    }
    return render(request, "products/list.html", context)


def load_more_products(request):
    try:
        product_type = request.GET.get("type")
        action = request.GET.get("action", "expand")  # 'expand' or 'collapse'
        category_slug = request.GET.get("category")

        ITEMS_PER_SECTION = 4

        # Get queryset
        model_map = {"nysc_kit": NyscKit, "nysc_tour": NyscTour, "church": Church}

        if product_type not in model_map:
            return HttpResponse(status=400)

        queryset = (
            model_map[product_type]
            .objects.filter(available=True)
            .select_related("category")
        )

        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)

        # Return either full or limited set based on action
        products = queryset if action == "expand" else queryset[:ITEMS_PER_SECTION]

        context = {
            "products": products,
            "is_expanded": action == "expand",
            "product_type": product_type,
            "category": category if category_slug else None,
        }

        return render(request, "products/partials/product_grid.html", context)
    except Exception as e:
        # Log the error if you have logging configured
        print(f"Error in load_more_products: {str(e)}")  # For development
        return HttpResponse(status=500)


def product_detail(request, product_type, id, slug):
    model = Cart.MODEL_MAPPING.get(product_type)
    if not model:
        raise Http404("Invalid product type")

    try:
        model = apps.get_model("products", model)
        product = get_object_or_404(model, id=id, slug=slug)
        template_name = f"products/{product_type}_detail.html"

        # Check if user is authenticated before querying measurements
        has_measurement = False
        if request.user.is_authenticated:
            has_measurement = not Measurement.objects.filter(user=request.user).exists()

        # Get content type for the comments system
        content_type = ContentType.objects.get_for_model(model).model

        context = {
            "product": product,
            "cart_add_form": CartAddProductForm(
                initial={"product_type": product_type, "quantity": 1}
            ),
            "clothes_sizes": Cart.get_clothes_sizes(),
            "has_measurement": has_measurement,
            # Add these for the comment system
            "content_type": content_type,
            "object_id": id,
        }
        return render(request, template_name, context)
    except LookupError:
        raise Http404("Product type not found")
