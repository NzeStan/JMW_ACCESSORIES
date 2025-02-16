from django import template

register = template.Library()


@register.filter
def get_range(value):
    """
    Filter to create a range of numbers.
    Usage: {% for i in 5|get_range %}
    """
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)
