"""
URL configuration for jmw project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Django admin
    path("i_must_win/", admin.site.urls),

    # API Documentation (OpenAPI/Swagger)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API Auth
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    path("api/auth/social/", include("accounts.urls")),

    # Local apps (API)
    path("api/products/", include("products.urls", namespace="products")),
    path("api/cart/", include("cart.urls", namespace="cart")),
    path("api/measurement/", include("measurement.urls", namespace="measurement")),
    path("api/feed/", include("feed.urls", namespace="feed")),
    path("api/order/", include("order.urls", namespace="order")),
    path("api/payment/", include("payment.urls", namespace="payment")),
    path("api/bulk_orders/", include("bulk_orders.urls", namespace="bulk_orders")),
    path("api/webhook/", include("webhook_router.urls")),
    path("api/generate/", include("orderitem_generation.urls")),
]
if settings.DEBUG: # new
    import debug_toolbar
    urlpatterns = [
    path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
