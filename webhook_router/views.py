from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from bulk_orders import views as bulk_orders_views
from payment import views as payment_views


@csrf_exempt
def router_webhook(request):
    payload = json.loads(request.body)
    reference = payload["data"]["reference"]

    if reference.startswith("ORDER-"):
        return bulk_orders_views.payment_webhook(request)
    return payment_views.payment_webhook(request)
