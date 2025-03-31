from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    return dictionary.get(key)

@register.filter
def currency(value):
    """Format value as Philippine Peso"""
    try:
        return f"₱{float(value):.2f}"
    except (ValueError, TypeError):
        return value
