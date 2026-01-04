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

# ============================================================================
# AVAILABLE ENDPOINTS - UPDATED!
# ============================================================================

# BULK ORDER LINKS:
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
# ✅ NEW: ORDER SUBMISSION (NO bulk_order_slug NEEDED!)
# POST   /api/bulk_orders/links/<slug>/submit_order/               # Submit order for this bulk order
#        Request body: { "email": "...", "full_name": "...", "size": "...", "coupon_code": "..." }
#        NO NEED for bulk_order_slug! It's in the URL!
#
# ORDER MANAGEMENT:
# GET    /api/bulk_orders/orders/                                  # List user's orders
# GET    /api/bulk_orders/orders/<id>/                             # Get specific order
# POST   /api/bulk_orders/orders/<id>/initialize_payment/          # Initialize payment for order
#
# COUPON MANAGEMENT:
# GET    /api/bulk_orders/coupons/                                 # List coupons (Admin)
# GET    /api/bulk_orders/coupons/?bulk_order_slug=<slug>          # Filter by bulk order
# POST   /api/bulk_orders/coupons/<id>/validate_coupon/            # Validate coupon
#
# PAYMENT:
# POST   /api/bulk_orders/payment/callback/                        # Payment webhook (Paystack)

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

# EXAMPLE 1: Submit order (user on page /bulk-order/church-2024-abc1/)
# POST /api/bulk_orders/links/church-2024-abc1/submit_order/
# {
#   "email": "john@example.com",
#   "full_name": "John Doe",
#   "size": "L",
#   "custom_name": "PASTOR JOHN",  // Only if custom_branding_enabled=True
#   "coupon_code": "ABC12345"      // Optional
# }

# EXAMPLE 2: Get coupons for specific bulk order
# GET /api/bulk_orders/coupons/?bulk_order_slug=church-2024-abc1

# EXAMPLE 3: Initialize payment
# POST /api/bulk_orders/orders/{order_id}/initialize_payment/