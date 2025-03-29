from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import timezone
from django.db import models
from .models import Category, MenuItem, Cart, CartItem, Order, OrderItem, Review, Reservation
from django.contrib.auth.forms import PasswordChangeForm

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


def user_login(request):
    """Handle user login with role-based redirects"""
    if request.user.is_authenticated:
        # If already logged in, redirect based on role
        if request.user.is_staff:
            return redirect('dashboard')
        return redirect('customer_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')

            # Redirect based on user role
            if user.is_staff:
                return redirect('dashboard')
            return redirect('customer_dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')

    return render(request, 'accounts/login.html')


def user_logout(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home')


@login_required
def user_dashboard(request):
    """User dashboard for managing restaurant data"""
    # Get today's date
    today = timezone.now().date()

    # Get counts and statistics
    categories = Category.objects.all()
    menu_items = MenuItem.objects.all()

    # Get recent orders
    recent_orders = Order.objects.order_by('-created_at')[:5]

    # Get popular menu items
    popular_items = MenuItem.objects.annotate(order_count=models.Count('orderitem')).order_by('-order_count')[:5]

    # Get recent reviews
    recent_reviews = Review.objects.select_related('user', 'menu_item').order_by('-created_at')[:5]

    # Calculate statistics
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(created_at__date=today).count()
    total_revenue = Order.objects.aggregate(models.Sum('total_amount'))['total_amount__sum'] or 0
    today_revenue = Order.objects.filter(created_at__date=today).aggregate(models.Sum('total_amount'))['total_amount__sum'] or 0

    context = {
        'categories': categories,
        'menu_items': menu_items,
        'recent_orders': recent_orders,
        'popular_items': popular_items,
        'recent_reviews': recent_reviews,
        'total_orders': total_orders,
        'today_orders': today_orders,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'active_section': 'dashboard'
    }

    return render(request, 'accounts/dashboard.html', context)


@login_required
def menu_items_list(request):
    """Display and manage menu items"""
    menu_items = MenuItem.objects.all().order_by('category', 'name')
    categories = Category.objects.all()

    context = {
        'menu_items': menu_items,
        'categories': categories,
        'active_section': 'menu_items'
    }

    return render(request, 'accounts/menu_items.html', context)


@login_required
def categories_list(request):
    """Display and manage categories"""
    categories = Category.objects.all()

    # Count menu items in each category
    for category in categories:
        category.item_count = MenuItem.objects.filter(category=category).count()

    if request.method == 'POST':
        # Handle category creation
        name = request.POST.get('name')
        description = request.POST.get('description')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')

        if not name:
            messages.error(request, 'Category name is required')
        else:
            try:
                category = Category.objects.create(
                    name=name,
                    description=description,
                    is_active=is_active,
                    image=image
                )
                messages.success(request, f'Category "{name}" has been added successfully')
                return redirect('categories')
            except Exception as e:
                messages.error(request, f'Error adding category: {str(e)}')

    context = {
        'categories': categories,
        'active_section': 'categories'
    }

    return render(request, 'accounts/categories.html', context)


@login_required
def edit_category(request, category_id):
    """Edit an existing category"""
    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        messages.error(request, 'Category not found')
        return redirect('categories')

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description')
        is_active = request.POST.get('is_active') == 'on'
        image = request.FILES.get('image')

        # Validate data
        if not name:
            messages.error(request, 'Category name is required')
            return redirect('categories')

        try:
            # Update category
            category.name = name
            category.description = description
            category.is_active = is_active

            # Only update image if a new one is provided
            if image:
                category.image = image

            category.save()
            messages.success(request, f'Category "{name}" has been updated successfully')
        except Exception as e:
            messages.error(request, f'Error updating category: {str(e)}')

    return redirect('categories')


@login_required
def delete_category(request, category_id):
    """Delete a category"""
    try:
        category = Category.objects.get(id=category_id)
        name = category.name

        # Check if category has menu items
        menu_items = MenuItem.objects.filter(category=category)
        menu_items_count = menu_items.count()

        if menu_items_count > 0 and request.method == 'GET':
            # Get all other categories for reassignment
            other_categories = Category.objects.exclude(id=category_id)

            context = {
                'category': category,
                'menu_items_count': menu_items_count,
                'other_categories': other_categories,
                'active_section': 'categories'
            }
            return render(request, 'accounts/delete_category_confirm.html', context)

        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'reassign':
                # Reassign menu items to another category
                new_category_id = request.POST.get('new_category')
                if not new_category_id:
                    messages.error(request, 'Please select a category for reassignment')
                    return redirect('categories')

                try:
                    new_category = Category.objects.get(id=new_category_id)
                    menu_items.update(category=new_category)
                    messages.success(request, f'Menu items reassigned to "{new_category.name}"')
                except Category.DoesNotExist:
                    messages.error(request, 'Target category not found')
                    return redirect('categories')

            elif action == 'delete':
                # Delete all menu items in this category
                menu_items.delete()
                messages.success(request, f'Deleted {menu_items_count} menu items from category "{name}"')

            elif action == 'orphan':
                # Set category to NULL for all menu items
                menu_items.update(category=None)
                messages.success(request, f'Removed category from {menu_items_count} menu items')

            # Now delete the category
            category.delete()
            messages.success(request, f'Category "{name}" has been deleted successfully')

    except Category.DoesNotExist:
        messages.error(request, 'Category not found')
    except Exception as e:
        messages.error(request, f'Error deleting category: {str(e)}')

    return redirect('categories')


@login_required
def orders_list(request):
    """Display and manage orders"""
    orders = Order.objects.all().order_by('-created_at')

    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        orders = orders.filter(status=status_filter)

    context = {
        'orders': orders,
        'status_filter': status_filter or 'all',
        'status_choices': Order.STATUS_CHOICES,
        'active_section': 'orders'
    }

    return render(request, 'accounts/orders.html', context)


@login_required
def reservations_list(request):
    """Display and manage reservations"""
    reservations = Reservation.objects.all().order_by('-date', '-time')

    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        reservations = reservations.filter(status=status_filter)

    # Filter by date range if provided
    today = timezone.now().date()
    date_filter = request.GET.get('date', 'upcoming')

    if date_filter == 'today':
        reservations = reservations.filter(date=today)
    elif date_filter == 'upcoming':
        reservations = reservations.filter(date__gte=today)
    elif date_filter == 'past':
        reservations = reservations.filter(date__lt=today)

    context = {
        'reservations': reservations,
        'status_filter': status_filter or 'all',
        'date_filter': date_filter,
        'status_choices': Reservation.STATUS_CHOICES,
        'active_section': 'reservations'
    }

    return render(request, 'accounts/reservations.html', context)


@login_required
def reviews_list(request):
    """Display and manage reviews"""
    reviews = Review.objects.all().select_related('user', 'menu_item').order_by('-created_at')

    # Filter by rating if provided
    rating_filter = request.GET.get('rating')
    if rating_filter and rating_filter.isdigit():
        reviews = reviews.filter(rating=int(rating_filter))

    context = {
        'reviews': reviews,
        'rating_filter': rating_filter,
        'active_section': 'reviews'
    }

    return render(request, 'accounts/reviews.html', context)


@login_required
def profile(request):
    """Display and handle user profile updates"""
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        
        # Update user
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        
        # If you have a UserProfile model with additional fields
        if hasattr(user, 'profile'):
            user.profile.phone = phone
            user.profile.save()
            
        user.save()
        messages.success(request, 'Profile updated successfully!')
        
    context = {
        'active_section': 'profile'
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def user_settings(request):
    """Display and edit user settings"""
    if request.method == 'POST':
        # Handle password change
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Keep user logged in
            messages.success(request, 'Password changed successfully')
            return redirect('user_settings')

    context = {
        'active_section': 'settings'
    }

    return render(request, 'accounts/settings.html', context)


@login_required
def add_menu_item(request):
    """Add a new menu item"""
    categories = Category.objects.filter(is_active=True)

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        description = request.POST.get('description')
        is_available = request.POST.get('is_available') == 'on'
        is_featured = request.POST.get('is_featured') == 'on'
        is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        spice_level = request.POST.get('spice_level')
        image = request.FILES.get('image')

        # Validate data
        if not (name and category_id and price and description):
            messages.error(request, 'Please fill in all required fields')
            return render(request, 'accounts/add_menu_item.html', {'categories': categories, 'active_section': 'menu_items'})

        try:
            # Create new menu item
            category = Category.objects.get(id=category_id)
            menu_item = MenuItem.objects.create(
                name=name,
                category=category,
                price=price,
                description=description,
                is_available=is_available,
                is_featured=is_featured,
                is_vegetarian=is_vegetarian,
                spice_level=spice_level,
                image=image
            )
            messages.success(request, f'Menu item "{name}" has been added successfully')
            return redirect('menu_items')
        except Exception as e:
            messages.error(request, f'Error adding menu item: {str(e)}')

    return render(request, 'accounts/add_menu_item.html', {'categories': categories, 'active_section': 'menu_items'})


@login_required
def edit_menu_item(request, item_id):
    """Edit an existing menu item"""
    try:
        menu_item = MenuItem.objects.get(id=item_id)
    except MenuItem.DoesNotExist:
        messages.error(request, 'Menu item not found')
        return redirect('menu_items')

    categories = Category.objects.filter(is_active=True)

    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        description = request.POST.get('description')
        is_available = request.POST.get('is_available') == 'on'
        is_featured = request.POST.get('is_featured') == 'on'
        is_vegetarian = request.POST.get('is_vegetarian') == 'on'
        spice_level = request.POST.get('spice_level')
        image = request.FILES.get('image')

        # Validate data
        if not (name and category_id and price and description):
            messages.error(request, 'Please fill in all required fields')
            return redirect('menu_items')

        try:
            # Update menu item
            menu_item.name = name
            menu_item.category = Category.objects.get(id=category_id)
            menu_item.price = price
            menu_item.description = description
            menu_item.is_available = is_available
            menu_item.is_featured = is_featured
            menu_item.is_vegetarian = is_vegetarian
            menu_item.spice_level = spice_level

            # Only update image if a new one is provided
            if image:
                menu_item.image = image

            menu_item.save()
            messages.success(request, f'Menu item "{name}" has been updated successfully')
        except Exception as e:
            messages.error(request, f'Error updating menu item: {str(e)}')

    return redirect('menu_items')


@login_required
def delete_menu_item(request, item_id):
    """Delete a menu item"""
    try:
        menu_item = MenuItem.objects.get(id=item_id)
        name = menu_item.name
        menu_item.delete()
        messages.success(request, f'Menu item "{name}" has been deleted successfully')
    except MenuItem.DoesNotExist:
        messages.error(request, 'Menu item not found')
    except Exception as e:
        messages.error(request, f'Error deleting menu item: {str(e)}')

    return redirect('menu_items')


@login_required
def customer_dashboard(request):
    """Customer dashboard for managing their orders and profile"""
    # Get user's orders
    user_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    recent_orders = user_orders[:5]
    
    # Get user's reviews
    user_reviews = Review.objects.filter(user=request.user).select_related('menu_item').order_by('-created_at')[:5]
    
    # Calculate statistics
    total_orders = user_orders.count()
    total_spent = user_orders.aggregate(models.Sum('total_amount'))['total_amount__sum'] or 0
    
    # Get favorite items (most ordered)
    favorite_items = MenuItem.objects.filter(
        orderitem__order__user=request.user
    ).annotate(
        order_count=models.Count('orderitem')
    ).order_by('-order_count')[:5]

    context = {
        'recent_orders': recent_orders,
        'user_reviews': user_reviews,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'favorite_items': favorite_items,
        'active_section': 'dashboard'
    }
    
    return render(request, 'accounts/customer_dashboard.html', context)


@login_required
def my_orders(request):
    """Display customer's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
        'active_section': 'orders'
    }
    
    return render(request, 'accounts/my_orders.html', context)


@login_required
def my_reviews(request):
    """Display customer's review history"""
    reviews = Review.objects.filter(user=request.user).select_related('menu_item').order_by('-created_at')
    
    context = {
        'reviews': reviews,
        'active_section': 'reviews'
    }
    
    return render(request, 'accounts/my_reviews.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {
        'form': form,
        'active_section': 'profile'
    })
