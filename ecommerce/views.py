from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Category, MenuItem, Cart, CartItem

def home(request):
    # Get active categories and available menu items
    categories = Category.objects.filter(is_active=True)
    menu_items = MenuItem.objects.filter(is_available=True)

    # Get featured items
    featured_items = menu_items.filter(is_featured=True)[:6]

    context = {
        'categories': categories,
        'menu_items': featured_items,
    }

    return render(request, 'home.html', context)

def filter_menu(request):
    """Filter menu items by category"""
    category_id = request.GET.get('category')

    # Get all available menu items
    menu_items = MenuItem.objects.filter(is_available=True)

    # Filter by category if provided
    if category_id:
        menu_items = menu_items.filter(category_id=category_id)

    context = {
        'menu_items': menu_items,
    }

    return render(request, 'components/home/menu_items_grid.html', context)

def menu(request):
    """Full menu page"""
    categories = Category.objects.filter(is_active=True)
    menu_items = MenuItem.objects.filter(is_available=True)

    context = {
        'categories': categories,
        'menu_items': menu_items,
    }

    return render(request, 'menu.html', context)

@require_POST
def add_to_cart(request, item_id):
    """Add an item to the cart"""
    menu_item = get_object_or_404(MenuItem, id=item_id, is_available=True)

    # For simplicity, we'll use session-based cart for non-logged in users
    if request.user.is_authenticated:
        # Get or create user's cart
        cart, created = Cart.objects.get_or_create(user=request.user)

        # Check if item already in cart
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            menu_item=menu_item,
            defaults={'quantity': 1}
        )

        # If item already exists, increment quantity
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
    else:
        # Initialize cart in session if it doesn't exist
        if 'cart' not in request.session:
            request.session['cart'] = {}

        # Get current cart from session
        cart = request.session['cart']
        item_id_str = str(item_id)

        # Add item or increment quantity
        if item_id_str in cart:
            cart[item_id_str] += 1
        else:
            cart[item_id_str] = 1

        # Save cart back to session
        request.session['cart'] = cart
        request.session.modified = True

    # Get cart count for response
    cart_count = get_cart_count(request)

    # Return cart count for HTMX to update the UI
    return HttpResponse(f'<span>{cart_count}</span>')

def get_cart_count(request):
    """Get the total number of items in the cart"""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            return sum(item.quantity for item in cart.cart_items.all())
        except Cart.DoesNotExist:
            return 0
    else:
        # Get cart from session
        cart = request.session.get('cart', {})
        return sum(cart.values())
