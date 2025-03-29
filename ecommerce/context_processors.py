from .views import get_cart_count

def cart_processor(request):
    """Add cart count to all templates"""
    return {
        'cart_count': get_cart_count(request)
    }
