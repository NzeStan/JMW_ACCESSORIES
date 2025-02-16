# email_tracking/views.py
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import EmailEvent, Bounce, Complaint
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta


@csrf_exempt
@require_POST
def sns_endpoint(request):
    try:
        payload = json.loads(request.body)

        # Handle SNS subscription confirmation
        if payload.get("Type") == "SubscriptionConfirmation":
            import urllib.request

            urllib.request.urlopen(payload["SubscribeURL"])
            return HttpResponse("Subscription confirmed!")

        # Parse message
        message = json.loads(payload["Message"])
        event_type = message.get("eventType")

        # Create base email event
        email_event = EmailEvent.objects.create(
            message_id=message.get("mail", {}).get("messageId"),
            event_type=event_type,
            recipient=message.get("mail", {}).get("destination", [])[0],
            timestamp=message.get("mail", {}).get("timestamp"),
            raw_data=message,
        )

        # Handle specific event types
        if event_type == "Bounce":
            bounce_data = message.get("bounce", {})
            Bounce.objects.create(
                email_event=email_event,
                bounce_type=bounce_data.get("bounceType"),
                bounce_subtype=bounce_data.get("bounceSubType"),
            )
        elif event_type == "Complaint":
            complaint_data = message.get("complaint", {})
            Complaint.objects.create(
                email_event=email_event,
                complaint_type=complaint_data.get("complaintFeedbackType"),
                feedback_id=complaint_data.get("feedbackId"),
            )

        return HttpResponse(status=200)
    except Exception as e:
        # Log the error
        return HttpResponse(status=500)


def dashboard(request):
    # Get last 24 hours of events
    last_24h = timezone.now() - timedelta(hours=24)
    recent_events = EmailEvent.objects.filter(timestamp__gte=last_24h).order_by(
        "-timestamp"
    )[:50]

    # Calculate stats
    total_sends = EmailEvent.objects.filter(event_type="Send").count()
    total_deliveries = EmailEvent.objects.filter(event_type="Delivery").count()
    total_bounces = Bounce.objects.count()
    total_complaints = Complaint.objects.count()

    delivery_rate = (total_deliveries / total_sends * 100) if total_sends > 0 else 0
    bounce_rate = (total_bounces / total_sends * 100) if total_sends > 0 else 0
    complaint_rate = (total_complaints / total_sends * 100) if total_sends > 0 else 0

    context = {
        "recent_events": recent_events,
        "total_sends": total_sends,
        "delivery_rate": round(delivery_rate, 2),
        "bounce_rate": round(bounce_rate, 2),
        "complaint_rate": round(complaint_rate, 2),
    }
    return render(request, "email_tracking/dashboard.html", context)
