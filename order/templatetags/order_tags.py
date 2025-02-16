from django import template
from django.db.models import Count

register = template.Library()


@register.filter
def get_order_type(order):
    """Returns a human-readable order type"""
    order_type = order.__class__.__name__
    if order_type == "NyscKitOrder":
        return "NYSC Kit"
    elif order_type == "NyscTourOrder":
        return "NYSC Tour"
    elif order_type == "ChurchOrder":
        return "Church Merchandise"
    return order_type


