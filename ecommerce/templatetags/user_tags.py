from django import template

register = template.Library()

@register.filter
def has_staff_profile(user):
    """Check if user has a staff profile"""
    return hasattr(user, 'staff_profile')

@register.filter
def get_staff_role(user):
    """Get user's staff role if they have a staff profile"""
    if hasattr(user, 'staff_profile'):
        return user.staff_profile.role
    return None
