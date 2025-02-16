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

urlpatterns = [
    # Django admin
    path("i_must_win/", admin.site.urls),
    # User management
    path("account/", include("allauth.urls")),
    path("__reload__/", include("django_browser_reload.urls")),
    # Local apps
    path("", include("pages.urls", namespace="pages")),
    path("products/", include("products.urls", namespace="products")),
    path("cart/", include("cart.urls", namespace="cart")),
    path("blog/", include("blog.urls", namespace="blog")),
    path("measurement/", include("measurement.urls", namespace="measurement")),
    path("feed/", include("feed.urls", namespace="feed")),
    path("order/", include("order.urls", namespace="order")),
    path("payment/", include("payment.urls", namespace="payment")),
    path("bulk_orders/", include("bulk_orders.urls", namespace="bulk_orders")),
    path("webhook/", include("webhook_router.urls")),
    path("api/", include("comments.urls")),
    path("email/", include("email_tracking.urls")),
    path("generate/", include("orderitem_generation.urls")),
]
if settings.DEBUG: # new
    import debug_toolbar
    urlpatterns = [
    path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
