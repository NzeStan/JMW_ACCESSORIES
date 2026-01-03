from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BulkOrderLinkViewSet, OrderEntryViewSet, CouponCodeViewSet, bulk_order_payment_webhook

app_name = "bulk_orders"

router = DefaultRouter()
router.register(r'links', BulkOrderLinkViewSet, basename='bulk-link')
router.register(r'orders', OrderEntryViewSet, basename='bulk-order')
router.register(r'coupons', CouponCodeViewSet, basename='bulk-coupon')

urlpatterns = [
    # Payment webhook (must be before router to avoid conflicts)
    path('payment/callback/', bulk_order_payment_webhook, name='payment-webhook'),
    
    # REST API routes
    path('', include(router.urls)),
]

# Available endpoints:
# GET    /api/bulk_orders/links/                                   # List all bulk orders
# POST   /api/bulk_orders/links/                                   # Create new bulk order
# GET    /api/bulk_orders/links/<slug>/                            # Get specific bulk order by slug
# PUT    /api/bulk_orders/links/<slug>/                            # Update bulk order
# DELETE /api/bulk_orders/links/<slug>/                            # Delete bulk order
# GET    /api/bulk_orders/links/<slug>/stats/                      # Get statistics
# POST   /api/bulk_orders/links/<slug>/generate_coupons/           # Generate coupons (Admin)
# GET    /api/bulk_orders/links/<slug>/download_pdf/               # Download PDF (Admin)
# GET    /api/bulk_orders/links/<slug>/download_word/              # Download Word (Admin)
# GET    /api/bulk_orders/links/<slug>/generate_size_summary/      # Download Excel (Admin)
#
# GET    /api/bulk_orders/orders/                                  # List user's orders
# POST   /api/bulk_orders/orders/                                  # Submit new order (requires bulk_order_slug in body)
# GET    /api/bulk_orders/orders/<id>/                             # Get specific order
# POST   /api/bulk_orders/orders/<id>/initialize_payment/          # Initialize payment for order
#
# GET    /api/bulk_orders/coupons/                                 # List coupons (Admin)
# POST   /api/bulk_orders/coupons/<id>/validate_coupon/            # Validate coupon
#
# POST   /api/bulk_orders/payment/callback/                        # Payment webhook (Paystack)