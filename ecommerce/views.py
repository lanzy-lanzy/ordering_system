from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import timezone
from django.db import models
from django.db.models import Count, Sum
from decimal import Decimal
from .models import Category, MenuItem, Cart, CartItem, Order, OrderItem, Review, Reservation, StaffProfile, CustomerProfile, Payment, Refund, ReservationPayment, StaffActivity
from django.contrib.auth.forms import PasswordChangeForm
from .forms import RegistrationForm, CheckoutForm, GCashPaymentForm, ReservationForm, ReservationPaymentForm


def redirect_based_on_role(user):
    """Redirect user based on their role"""
    print(f"Redirecting user {user.username} based on role")

    # First check if user is a superuser - this takes precedence over all other roles
    if user.is_superuser:
        print(f"User {user.username} is superuser, redirecting to admin dashboard")
        return redirect('admin_dashboard')

    # Check if user has a staff profile with a specific role
    if hasattr(user, 'staff_profile'):
        role = user.staff_profile.role
        print(f"User {user.username} has staff profile with role: {role}")

        # Check role and redirect accordingly
        if role == 'CASHIER':
            print(f"User {user.username} is a cashier, redirecting to cashier dashboard")
            return redirect('cashier_dashboard')
        elif role == 'MANAGER':
            print(f"User {user.username} is a manager, redirecting to manager dashboard")
            return redirect('manager_dashboard')
        elif role == 'ADMIN':
            print(f"User {user.username} is an admin, redirecting to admin dashboard")
            return redirect('admin_dashboard')
        elif role == 'CUSTOMER':
            # This is a regular customer
            print(f"User {user.username} has CUSTOMER role, redirecting to customer dashboard")
            return redirect('customer_dashboard')

    # Check if user is a regular customer (has customer_profile but is not staff)
    if hasattr(user, 'customer_profile') and not user.is_staff:
        print(f"User {user.username} is a regular customer, redirecting to customer dashboard")
        return redirect('customer_dashboard')

    # Default redirects based on staff status
    if user.is_staff:
        print(f"User {user.username} is staff, redirecting to admin dashboard")
        return redirect('admin_dashboard')

    # Final fallback - send to customer dashboard
    print(f"User {user.username} has no specific role, redirecting to customer dashboard")
    return redirect('customer_dashboard')


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


def view_cart(request):
    """View the cart contents"""
    cart_items = []
    total = 0

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            # Use cart_items.all() directly - it already includes the cart item ID
            cart_items = cart.cart_items.all()
            total = cart.total
        except Cart.DoesNotExist:
            pass
    else:
        # Get cart from session
        session_cart = request.session.get('cart', {})

        # Convert session cart to cart items
        if session_cart:
            for item_id, quantity in session_cart.items():
                try:
                    menu_item = MenuItem.objects.get(id=item_id)
                    cart_items.append({
                        'menu_item': menu_item,
                        'quantity': quantity,
                        'subtotal': menu_item.price * quantity,
                        'id': item_id  # Add the item_id for use in templates
                    })
                    total += menu_item.price * quantity
                except MenuItem.DoesNotExist:
                    pass

    # Calculate tax (10%)
    tax = total * Decimal('0.1')
    grand_total = total + tax

    return render(request, 'cart/view_cart.html', {
        'cart_items': cart_items,
        'total': total,
        'tax': tax,
        'grand_total': grand_total
    })


def get_occupied_tables():
    """Get a list of currently occupied tables"""
    # Get all active dine-in orders (orders that are not completed or cancelled)
    active_orders = Order.objects.filter(
        order_type='DINE_IN',
        status__in=['PENDING', 'PREPARING', 'READY']
    )

    # Extract table numbers from active orders
    occupied_tables = [order.table_number for order in active_orders if order.table_number]

    return occupied_tables


@login_required
def checkout(request):
    """Checkout process"""
    # Get cart items and total
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.cart_items.all()

        if not cart_items.exists():
            messages.error(request, 'Your cart is empty. Please add items before checkout.')
            return redirect('view_cart')

        subtotal = cart.total
        tax = subtotal * Decimal('0.1')  # 10% tax
        total = subtotal + tax
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty. Please add items before checkout.')
        return redirect('view_cart')

    # Get occupied tables for dine-in orders
    occupied_tables = get_occupied_tables()

    if request.method == 'POST':
        # Get form data
        order_type = request.POST.get('order_type', 'PICKUP')
        table_number = request.POST.get('table_number', '')
        number_of_guests = request.POST.get('number_of_guests', 2)
        special_instructions = request.POST.get('special_instructions', '')

        # Convert number_of_guests to integer
        try:
            number_of_guests = int(number_of_guests)
        except (ValueError, TypeError):
            number_of_guests = 2

        # Process order data

        # Set default values based on order type
        delivery_address = ''
        contact_number = ''
        payment_status = 'PENDING'
        order_status = 'PENDING'

        # Customize based on order type
        if order_type == 'PICKUP':
            delivery_address = 'Pickup at restaurant'
        elif order_type == 'DELIVERY':
            delivery_address = request.user.customer_profile.address if hasattr(request.user, 'customer_profile') and request.user.customer_profile.address else 'Please update your address'
            contact_number = request.user.customer_profile.phone if hasattr(request.user, 'customer_profile') and request.user.customer_profile.phone else ''
        elif order_type == 'DINE_IN':
            # For dine-in orders, we need table number and guests
            if not table_number:
                messages.error(request, 'Please select a table for dine-in orders.')
                return render(request, 'checkout/checkout.html', {
                    'form': CheckoutForm(user=request.user, data=request.POST),
                    'cart_items': cart_items,
                    'subtotal': subtotal,
                    'tax': tax,
                    'total': total,
                    'occupied_tables': occupied_tables
                })

            # Set dine-in specific values
            order_status = 'PREPARING'  # Dine-in orders start in preparing status
            # All orders should start with PENDING payment status to go through payment flow
            payment_status = 'PENDING'

        # Create the order with all the collected information
        order = Order.objects.create(
            user=request.user,
            status=order_status,
            order_type=order_type,
            payment_method='GCASH',
            payment_status=payment_status,
            total_amount=subtotal,
            tax_amount=tax,
            delivery_fee=0,  # You can add delivery fee logic here
            discount_amount=0,  # You can add discount logic here
            delivery_address=delivery_address,
            contact_number=contact_number,
            table_number=table_number,
            number_of_guests=number_of_guests,
            special_instructions=special_instructions,
            preparing_at=timezone.now() if order_type == 'DINE_IN' else None  # Set preparing timestamp for dine-in
        )

        # Add order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                menu_item=cart_item.menu_item,
                quantity=cart_item.quantity,
                price=cart_item.menu_item.price,
                special_instructions=cart_item.special_instructions
            )

        # Clear the cart
        cart.cart_items.all().delete()

        # Order created successfully

        # Set success message
        if order_type == 'DINE_IN':
            messages.success(request, 'Your table has been reserved! Please complete the payment to confirm your order.')
        else:
            messages.success(request, 'Your order has been placed! Please complete the payment.')

        # Create payment URL and redirect
        payment_url = reverse('gcash_payment', kwargs={'order_id': order.id})
        return redirect(payment_url)
    else:
        # Check for URL parameters
        initial_data = {}
        if 'table' in request.GET:
            initial_data['table_number'] = request.GET.get('table')

        if 'order_type' in request.GET:
            initial_data['order_type'] = request.GET.get('order_type')

        form = CheckoutForm(user=request.user, initial=initial_data)

    return render(request, 'checkout/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'occupied_tables': occupied_tables
    })


@login_required
def gcash_payment(request, order_id):
    """GCash payment page with QR code"""
    print(f"GCash payment view called with order_id: {order_id}")
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        print(f"Order found: {order}")

        # Check if order is already paid
        if order.payment_status == 'PAID':
            messages.info(request, 'This order has already been paid.')
            return redirect('order_confirmation', order_id=order.id)

        # Check if payment exists
        payment = Payment.objects.filter(order=order).first()
        if not payment:
            # Create a new payment record
            payment = Payment.objects.create(
                order=order,
                amount=order.total_amount + order.tax_amount + order.delivery_fee - order.discount_amount,
                payment_method='GCASH',
                status='PENDING'
            )
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('view_cart')

    if request.method == 'POST':
        form = GCashPaymentForm(request.POST, request.FILES, instance=payment)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.status = 'COMPLETED'  # Auto-approve for now, in production this would be verified by staff
            payment.verification_date = timezone.now()
            payment.save()

            # Update order status
            order.payment_status = 'PAID'
            order.status = 'PREPARING'  # Move to preparing status
            order.save()

            messages.success(request, 'Payment verified successfully! Your order is now being prepared.')
            return redirect('order_confirmation', order_id=order.id)
    else:
        form = GCashPaymentForm(instance=payment)

    return render(request, 'checkout/gcash_payment.html', {
        'order': order,
        'payment': payment,
        'form': form
    })


@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order_items = order.order_items.all()
        payment = Payment.objects.filter(order=order).first()
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('view_cart')

    return render(request, 'checkout/order_confirmation.html', {
        'order': order,
        'order_items': order_items,
        'payment': payment
    })


@require_POST
def update_cart_item(request, item_id):
    """Update the quantity of an item in the cart"""
    action = request.POST.get('action')
    cart_item_id = request.POST.get('cart_item_id')  # Get the cart item ID if provided

    if action not in ['increase', 'decrease', 'remove']:
        return JsonResponse({'error': 'Invalid action'}, status=400)

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)

            # If cart_item_id is provided, use it to find the cart item
            if cart_item_id:
                try:
                    cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)
                    menu_item_id = cart_item.menu_item.id  # Store for potential new item creation

                    if action == 'increase':
                        cart_item.quantity += 1
                        cart_item.save()
                    elif action == 'decrease':
                        if cart_item.quantity > 1:
                            cart_item.quantity -= 1
                            cart_item.save()
                        else:
                            cart_item.delete()
                    elif action == 'remove':
                        cart_item.delete()

                except CartItem.DoesNotExist:
                    # If cart item not found by ID, fall back to menu_item_id
                    pass

            # If no cart_item_id or cart item not found, use menu_item_id
            if not cart_item_id or 'pass' in locals():
                try:
                    cart_item = CartItem.objects.get(cart=cart, menu_item_id=item_id)

                    if action == 'increase':
                        cart_item.quantity += 1
                        cart_item.save()
                    elif action == 'decrease':
                        if cart_item.quantity > 1:
                            cart_item.quantity -= 1
                            cart_item.save()
                        else:
                            cart_item.delete()
                    elif action == 'remove':
                        cart_item.delete()

                except CartItem.DoesNotExist:
                    if action == 'increase':
                        # If the item doesn't exist and we're trying to increase, create it
                        menu_item = get_object_or_404(MenuItem, id=item_id)
                        CartItem.objects.create(cart=cart, menu_item=menu_item, quantity=1)

        except Cart.DoesNotExist:
            return JsonResponse({'error': 'Cart not found'}, status=404)
    else:
        # Handle session cart
        cart = request.session.get('cart', {})
        item_id_str = str(item_id)

        if action == 'increase':
            if item_id_str in cart:
                cart[item_id_str] += 1
            else:
                cart[item_id_str] = 1
        elif action == 'decrease':
            if item_id_str in cart and cart[item_id_str] > 1:
                cart[item_id_str] -= 1
            elif item_id_str in cart:
                del cart[item_id_str]
        elif action == 'remove':
            if item_id_str in cart:
                del cart[item_id_str]

        request.session['cart'] = cart
        request.session.modified = True

    # Redirect back to the cart page
    return redirect('view_cart')


def user_login(request):
    print("User login view called")
    if request.user.is_authenticated:
        print(f"User {request.user.username} is already authenticated")
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        print(f"Login attempt for username: {username}")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            print(f"Authentication successful for user: {username}")

            # Check if user is blacklisted
            if hasattr(user, 'customer_profile') and user.customer_profile.is_blacklisted:
                print(f"User {username} is blacklisted, login denied")
                messages.error(request, 'Your account has been blacklisted. Please contact customer support for assistance.')
                return render(request, 'accounts/login.html')

            login(request, user)

            # Direct role-based redirection
            if hasattr(user, 'staff_profile'):
                role = user.staff_profile.role
                print(f"User {username} has role: {role}")

                if role == 'CASHIER':
                    print(f"User {username} is a cashier, redirecting to cashier dashboard")
                    return redirect('cashier_dashboard')
                elif role == 'MANAGER':
                    print(f"User {username} is a manager, redirecting to manager dashboard")
                    return redirect('manager_dashboard')
                elif role == 'ADMIN':
                    print(f"User {username} is an admin, redirecting to admin dashboard")
                    return redirect('admin_dashboard')

            # For other roles, use the standard redirection logic
            return redirect_based_on_role(user)
        else:
            print(f"Authentication failed for username: {username}")
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')


def user_register(request):
    """Handle user registration"""
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in after registration
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to 5th Avenue Grill and Restobar.')
            # Ensure the user has a customer profile before redirecting
            if hasattr(user, 'customer_profile'):
                return redirect('customer_dashboard')
            else:
                # This should not happen with our updated form, but just in case
                from .models import CustomerProfile
                CustomerProfile.objects.create(user=user)
                return redirect('customer_dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def user_logout(request):
    """Handle user logout"""
    print(f"Logout request received for user: {request.user.username}")
    print(f"Request method: {request.method}")

    # Log the user out
    logout(request)

    # Add success message
    messages.success(request, 'You have been successfully logged out.')

    # Redirect to login page instead of home
    print("Redirecting to login page after logout")
    return redirect('login')


@login_required
def user_dashboard(request):
    """User dashboard for managing restaurant data"""
    # First check if user is a superuser - this takes precedence over all other roles
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    # Check if user has a staff profile and redirect accordingly
    if hasattr(request.user, 'staff_profile'):
        # Redirect to the appropriate dashboard based on role
        return redirect_based_on_role(request.user)

    # If user is staff but doesn't have a staff profile, show the general dashboard
    if request.user.is_staff:
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

    # If not staff, redirect to customer dashboard
    return redirect('customer_dashboard')


@login_required
def menu_items_list(request):
    """Display and manage menu items"""
    category_id = request.GET.get('category')
    menu_items = MenuItem.objects.all().order_by('category', 'name')
    categories = Category.objects.all()

    # Filter by category if provided
    selected_category = None
    if category_id:
        try:
            selected_category = Category.objects.get(id=category_id)
            menu_items = menu_items.filter(category=selected_category)
        except Category.DoesNotExist:
            pass

    context = {
        'menu_items': menu_items,
        'categories': categories,
        'selected_category': selected_category,
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
def make_reservation(request):
    """Allow registered customers to make a reservation with table selection and menu items"""
    # Get available tables
    occupied_tables = get_occupied_tables()

    # Get menu items and categories for ordering
    menu_items = MenuItem.objects.filter(is_available=True)
    categories = Category.objects.filter(is_active=True)

    # Get user profile information
    user_email = request.user.email
    user_phone = ''
    if hasattr(request.user, 'customer_profile'):
        user_phone = request.user.customer_profile.phone

    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user if request.user.is_authenticated else None)
        if form.is_valid():
            with transaction.atomic():
                # Save the reservation
                reservation = form.save(commit=False)
                reservation.user = request.user  # Always associate with the logged-in user

                # Add table number if selected
                table_number = request.POST.get('table_number')
                if table_number:
                    reservation.table_number = table_number

                # Process menu items if any were selected
                menu_items_data = request.POST.get('menu_items_data')
                total_amount = Decimal('0.00')

                if menu_items_data:
                    try:
                        import json
                        menu_items_json = json.loads(menu_items_data)

                        if menu_items_json and len(menu_items_json) > 0:
                            # Calculate total amount for the reservation
                            for item in menu_items_json:
                                menu_item = MenuItem.objects.get(id=item['id'])
                                quantity = item['quantity']
                                total_amount += menu_item.price * Decimal(str(quantity))
                    except Exception as e:
                        # Log the error but continue with the reservation
                        print(f"Error processing menu items: {str(e)}")

                # Set the total amount for the reservation
                reservation.total_amount = total_amount
                reservation.save()

                # Store menu items in session for later use
                request.session['reservation_menu_items'] = menu_items_data
                request.session['reservation_id'] = reservation.id

                # Check if this is an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Reservation created successfully.',
                        'reservation_id': reservation.id,
                        'redirect_url': reverse('reservation_payment', args=[reservation.id])
                    })
                else:
                    # Redirect to payment page for non-AJAX requests
                    return redirect('reservation_payment', reservation_id=reservation.id)
        else:
            # If AJAX request and form is invalid
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]

                # Log the errors for debugging
                print(f"Form validation errors: {errors}")

                # Check specifically for time field errors
                if 'time' in errors:
                    print(f"Time field error: {errors['time']}")
                    print(f"Time value submitted: {request.POST.get('time')}")

                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors below.',
                    'errors': errors
                })
    else:
        form = ReservationForm(initial={
            'name': request.user.get_full_name() or request.user.username,
            'email': user_email,
            'phone': user_phone
        }, user=request.user)

    context = {
        'form': form,
        'occupied_tables': occupied_tables,
        'menu_items': menu_items,
        'categories': categories,
        'active_section': 'make_reservation'
    }

    return render(request, 'reservations/make_reservation.html', context)


@login_required
def reservation_payment(request, reservation_id):
    """GCash payment page for reservations"""
    try:
        reservation = Reservation.objects.get(id=reservation_id, user=request.user)

        # Check if reservation is already paid
        if reservation.payment_status == 'PAID':
            messages.info(request, 'This reservation has already been paid.')
            return redirect('my_reservations')

        # Get or create a payment record
        payment, created = ReservationPayment.objects.get_or_create(
            reservation=reservation,
            status='PENDING',
            defaults={
                'amount': Decimal('0.00'),  # Will be set based on payment type
                'payment_method': 'GCASH'
            }
        )

        if request.method == 'POST':
            form = ReservationPaymentForm(request.POST, request.FILES, instance=payment)
            if form.is_valid():
                payment = form.save(commit=False)

                # Calculate payment amount based on payment type
                payment_type = form.cleaned_data['payment_type']
                if payment_type == 'FULL':
                    payment.amount = reservation.total_amount
                else:  # DEPOSIT (50%)
                    payment.amount = reservation.total_amount * Decimal('0.5')

                payment.status = 'PENDING'  # Will be verified by staff
                payment.save()

                # Process menu items if any were selected
                menu_items_data = request.session.get('reservation_menu_items')
                if menu_items_data:
                    try:
                        import json
                        menu_items_json = json.loads(menu_items_data)

                        # Create an order for the menu items
                        order = Order.objects.create(
                            user=request.user,
                            status='PENDING',
                            order_type='DINE_IN',
                            payment_method='GCASH',
                            payment_status='PENDING',
                            total_amount=reservation.total_amount,
                            tax_amount=Decimal('0.00'),
                            table_number=reservation.table_number,
                            number_of_guests=reservation.party_size,
                            special_instructions=reservation.special_requests
                        )

                        # Add order items
                        for item in menu_items_json:
                            menu_item = MenuItem.objects.get(id=item['id'])
                            OrderItem.objects.create(
                                order=order,
                                menu_item=menu_item,
                                quantity=item['quantity'],
                                price=menu_item.price
                            )

                        # Clear session data
                        if 'reservation_menu_items' in request.session:
                            del request.session['reservation_menu_items']
                        if 'reservation_id' in request.session:
                            del request.session['reservation_id']
                    except Exception as e:
                        messages.error(request, f"Error processing menu items: {str(e)}")

                messages.success(request, 'Your payment has been submitted and is awaiting verification. You will receive a confirmation once it is approved.')
                return redirect('my_reservations')
        else:
            form = ReservationPaymentForm(instance=payment)

        return render(request, 'reservations/reservation_payment.html', {
            'reservation': reservation,
            'payment': payment,
            'form': form
        })
    except Reservation.DoesNotExist:
        messages.error(request, 'Reservation not found.')
        return redirect('my_reservations')


@login_required
def my_reservations(request):
    """Display a customer's reservations"""
    reservations = Reservation.objects.filter(user=request.user).order_by('-date', '-time')

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

    # Get data for reservation modal
    occupied_tables = get_occupied_tables()
    menu_items = MenuItem.objects.filter(is_available=True)
    categories = Category.objects.filter(is_active=True)

    context = {
        'reservations': reservations,
        'status_filter': status_filter or 'all',
        'date_filter': date_filter,
        'status_choices': Reservation.STATUS_CHOICES,
        'active_section': 'my_reservations',
        # Reservation modal data
        'occupied_tables': occupied_tables,
        'menu_items': menu_items,
        'categories': categories
    }

    return render(request, 'reservations/my_reservations.html', context)


@login_required
def cancel_reservation(request, reservation_id):
    """Allow customers to cancel their reservations"""
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    if reservation.status == 'CONFIRMED':
        messages.warning(request, 'This reservation has already been confirmed. Please contact us to cancel it.')
    else:
        reservation.status = 'CANCELLED'
        reservation.save()
        messages.success(request, 'Your reservation has been cancelled successfully.')

    return redirect('my_reservations')


@login_required
@permission_required('ecommerce.change_reservation', raise_exception=True)
def reservations_list(request):
    """Display and manage reservations for staff"""
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
@permission_required('ecommerce.change_reservation', raise_exception=True)
def update_reservation_status(request, reservation_id):
    """Update the status of a reservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)

    # Get the next parameter for redirect
    next_page = request.GET.get('next', 'reservations')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Reservation.STATUS_CHOICES):
            reservation.status = new_status
            reservation.save()

            # Log the activity
            StaffActivity.objects.create(
                staff=request.user,
                action='UPDATE_RESERVATION',
                details=f"Updated reservation #{reservation_id} status to {dict(Reservation.STATUS_CHOICES)[new_status]}"
            )

            messages.success(request, f'Reservation status updated to {dict(Reservation.STATUS_CHOICES)[new_status]}')
        else:
            messages.error(request, 'Invalid status provided')

    # Handle GET requests with status parameter (for quick actions from dashboard)
    elif request.method == 'GET' and 'status' in request.GET:
        new_status = request.GET.get('status')
        if new_status in dict(Reservation.STATUS_CHOICES):
            reservation.status = new_status
            reservation.save()

            # Log the activity
            StaffActivity.objects.create(
                staff=request.user,
                action='UPDATE_RESERVATION',
                details=f"Updated reservation #{reservation_id} status to {dict(Reservation.STATUS_CHOICES)[new_status]}"
            )

            messages.success(request, f'Reservation status updated to {dict(Reservation.STATUS_CHOICES)[new_status]}')
        else:
            messages.error(request, 'Invalid status provided')

    # Redirect based on the next parameter
    if next_page == 'manager_dashboard':
        return redirect('manager_dashboard')
    elif next_page == 'reservations_dashboard':
        return redirect('reservations_dashboard')
    else:
        return redirect('reservations')


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
        profile_picture = request.FILES.get('profile_picture')

        # Update user
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email

        # Update staff profile if it exists
        if hasattr(user, 'staff_profile'):
            if phone:
                user.staff_profile.phone = phone

            # Handle profile picture upload
            if profile_picture:
                user.staff_profile.profile_picture = profile_picture

            user.staff_profile.save()

        # Update customer profile if it exists
        if hasattr(user, 'customer_profile'):
            if phone:
                user.customer_profile.phone = phone

            # Handle profile picture upload
            if profile_picture:
                user.customer_profile.profile_picture = profile_picture

            user.customer_profile.save()
        # If you have a UserProfile model with additional fields
        elif hasattr(user, 'profile'):
            user.profile.phone = phone
            user.profile.save()

        user.save()
        messages.success(request, 'Profile updated successfully!')

    # Get staff profile if it exists
    staff_profile = None
    if hasattr(request.user, 'staff_profile'):
        staff_profile = request.user.staff_profile

    context = {
        'active_section': 'profile',
        'staff_profile': staff_profile
    }

    # Choose the appropriate template based on user role
    if request.user.is_staff:
        return render(request, 'accounts/admin_profile.html', context)
    else:
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

    # Get data for reservation modal
    occupied_tables = get_occupied_tables()
    menu_items = MenuItem.objects.filter(is_available=True)
    categories = Category.objects.filter(is_active=True)

    context = {
        'recent_orders': recent_orders,
        'user_reviews': user_reviews,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'favorite_items': favorite_items,
        'active_section': 'dashboard',
        # Reservation modal data
        'occupied_tables': occupied_tables,
        'menu_items': menu_items,
        'categories': categories
    }

    return render(request, 'accounts/customer_dashboard.html', context)


@login_required
def my_orders(request):
    """Display customer's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

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

    return render(request, 'accounts/my_orders.html', context)


@login_required
def view_customer_order(request, order_id):
    """View detailed information about a customer's order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.order_items.all()

    # Get payment information if available
    payment = Payment.objects.filter(order=order).first()

    # Calculate time elapsed since order creation
    time_elapsed = None
    if order.created_at:
        time_elapsed = timezone.now() - order.created_at

    # Get order timeline data
    timeline_events = [
        {'time': order.created_at, 'status': 'Order Placed', 'icon': 'fa-shopping-cart', 'color': 'text-blue-400'}
    ]

    if order.preparing_at:
        timeline_events.append({'time': order.preparing_at, 'status': 'Preparing', 'icon': 'fa-utensils', 'color': 'text-yellow-400'})

    if order.ready_at:
        timeline_events.append({'time': order.ready_at, 'status': 'Ready for Pickup', 'icon': 'fa-check-circle', 'color': 'text-green-400'})

    if order.completed_at:
        timeline_events.append({'time': order.completed_at, 'status': 'Completed', 'icon': 'fa-flag-checkered', 'color': 'text-gray-400'})

    if order.cancelled_at:
        timeline_events.append({'time': order.cancelled_at, 'status': 'Cancelled', 'icon': 'fa-times-circle', 'color': 'text-red-400'})

    # Sort timeline events by time
    timeline_events = sorted([event for event in timeline_events if event['time']], key=lambda x: x['time'])

    context = {
        'order': order,
        'order_items': order_items,
        'payment': payment,
        'time_elapsed': time_elapsed,
        'timeline_events': timeline_events,
        'active_section': 'orders'
    }

    return render(request, 'accounts/view_customer_order.html', context)


@login_required
def customer_cancel_order(request, order_id):
    """Allow customers to cancel their own orders with restrictions"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Check if order can be cancelled by customer
    # Only allow cancellation if order is still pending and within a time window (15 minutes)
    time_window = timezone.now() - timezone.timedelta(minutes=15)

    if order.status != 'PENDING' or order.created_at < time_window:
        messages.error(request, 'This order can no longer be cancelled online. Please contact customer support.')
        return redirect('my_orders')

    if request.method == 'POST':
        cancellation_reason = request.POST.get('cancellation_reason', 'CUSTOMER_REQUEST')
        cancellation_notes = request.POST.get('cancellation_notes', 'Customer cancelled online')

        # Begin transaction to ensure all changes are atomic
        with transaction.atomic():
            # 1. Update order status
            order.status = 'CANCELLED'
            order.cancelled_at = timezone.now()
            order.cancellation_reason = cancellation_reason
            order.cancellation_notes = cancellation_notes
            order.cancelled_by = request.user
            order.save()

            # 2. Handle payment if already paid
            if order.payment_status == 'PAID':
                # Create refund record
                refund = Refund.objects.create(
                    order=order,
                    amount=order.grand_total,
                    reason=f"Customer cancelled order online",
                    status='PENDING',
                    initiated_by=request.user,
                    notes=cancellation_notes
                )

                # Update payment status
                order.payment_status = 'REFUNDED'
                order.save(update_fields=['payment_status'])

                # Update any existing payments
                for payment in Payment.objects.filter(order=order, status='COMPLETED'):
                    payment.status = 'REFUNDED'
                    payment.save()

                messages.info(request, f'A refund of ₱{order.grand_total} has been initiated for this order')

            # 3. Free up table reservation (for dine-in)
            if order.order_type == 'DINE_IN' and order.table_number:
                messages.info(request, f'Your table reservation has been cancelled')

        messages.success(request, f'Your order has been cancelled successfully')
        return redirect('my_orders')

    context = {
        'order': order,
        'cancellation_reasons': Order.CANCELLATION_REASON_CHOICES,
        'active_section': 'orders'
    }

    return render(request, 'customer/cancel_order.html', context)


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

    context = {
        'form': form,
        'active_section': 'profile'
    }

    # Choose the appropriate template based on user role
    if request.user.is_staff:
        return render(request, 'accounts/admin_change_password.html', context)
    else:
        return render(request, 'accounts/change_password.html', context)


@login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    if not request.user.is_superuser and not (hasattr(request.user, 'staff_profile') and request.user.staff_profile.role == 'ADMIN'):
        return redirect('home')

    today = timezone.now().date()

    # Calculate statistics
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(created_at__date=today).count()
    total_revenue = Order.objects.aggregate(models.Sum('total_amount'))['total_amount__sum'] or 0
    today_revenue = Order.objects.filter(created_at__date=today).aggregate(models.Sum('total_amount'))['total_amount__sum'] or 0
    pending_reservations = Reservation.objects.filter(status='PENDING').count()
    today_reservations = Reservation.objects.filter(date=today).count()

    # Get popular items and recent reviews
    popular_items = MenuItem.objects.annotate(order_count=Count('orderitem')).order_by('-order_count')[:5]
    recent_reviews = Review.objects.select_related('user', 'menu_item').order_by('-created_at')[:5]

    context = {
        'total_orders': total_orders,
        'today_orders': today_orders,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'pending_reservations': pending_reservations,
        'today_reservations': today_reservations,
        'popular_items': popular_items,
        'recent_reviews': recent_reviews,
    }

    return render(request, 'admin/dashboard.html', context)
