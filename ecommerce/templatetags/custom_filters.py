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

@register.filter
def split(value, arg):
    """Split a string by a delimiter"""
    return value.split(arg)

@register.filter
def sum_attr(items, attr):
    """Sum a specific attribute across a list of dictionaries"""
    try:
        return sum(float(item[attr]) if item[attr] is not None else 0 for item in items)
    except (KeyError, TypeError, ValueError):
        return 0

@register.filter
def js(value):
    """Pass through filter for JavaScript code"""
    return value
