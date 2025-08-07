# templatetags/mathfilters.py
from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiplies the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divides the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def sub(value, arg):
    """Subtracts the argument from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calculates percentage of value from total."""
    try:
        return round((float(value) / float(total)) * 100, 1) if float(total) > 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0