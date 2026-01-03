from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from bulk_orders import views as bulk_orders_views
from payment import views as payment_views


@csrf_exempt
def router_webhook(request):
    """
    Smart webhook router that directs payments based on reference format:
    - ORDER-{bulk_order_id}-{order_entry_id} → Bulk Orders
    - JMW-* or other formats → Regular Orders
    """
    try:
        payload = json.loads(request.body)
        reference = payload.get("data", {}).get("reference", "")
        
        # Route to bulk orders if reference starts with ORDER-
        if reference.startswith("ORDER-"):
            return bulk_orders_views.bulk_order_payment_webhook(request)
        
        # Route to regular payment processing for all other references
        return payment_views.payment_webhook(request)
        
    except json.JSONDecodeError:
        return HttpResponse(status=400)
    except Exception:
        # Fallback to regular payment processing
        return payment_views.payment_webhook(request)