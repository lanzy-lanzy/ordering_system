from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.http import JsonResponse
from .models import CustomerProfile, Order, StaffActivity
from django.core.paginator import Paginator

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required
@permission_required('ecommerce.manage_customers', raise_exception=True)
def customer_list(request):
    """Display list of customers with filtering and search"""
    # Get search query and filters
    query = request.GET.get('q', '')
    blacklist_filter = request.GET.get('blacklist', '')

    # Base queryset - only get regular users (not staff)
    customers = User.objects.filter(
        is_staff=False,
        is_superuser=False
    )

    # Apply search filter if provided
    if query:
        customers = customers.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

    # Get list of users that have customer profiles
    users_with_profiles = list(CustomerProfile.objects.values_list('user_id', flat=True))

    # Create profiles for users that don't have them
    for customer in customers:
        if customer.id not in users_with_profiles:
            CustomerProfile.objects.create(user=customer)
            messages.info(request, f"Created missing profile for user {customer.username}")

    # Now we can safely use select_related and filter by profile
    customers = customers.select_related('customer_profile')

    # Apply blacklist filter if provided
    if blacklist_filter:
        is_blacklisted = blacklist_filter == 'blacklisted'
        customers = customers.filter(customer_profile__is_blacklisted=is_blacklisted)

    # Add order count and total spent
    for customer in customers:
        customer.order_count = Order.objects.filter(user=customer).count()
        customer.total_spent = Order.objects.filter(user=customer).aggregate(
            total=Sum('total_amount'))['total'] or 0

    # Paginate results
    paginator = Paginator(customers, 20)  # Show 20 customers per page
    page_number = request.GET.get('page', 1)
    customer_page = paginator.get_page(page_number)

    context = {
        'customer_page': customer_page,
        'query': query,
        'blacklist_filter': blacklist_filter,
        'active_section': 'customers'
    }

    return render(request, 'accounts/customer_list.html', context)

@login_required
@permission_required('ecommerce.manage_customers', raise_exception=True)
def customer_detail(request, user_id):
    """Display customer details and allow blacklisting/unblacklisting"""
    customer = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)

    # Check if customer has a profile, create one if not
    try:
        customer_profile = customer.customer_profile
    except CustomerProfile.DoesNotExist:
        # Create a new customer profile
        customer_profile = CustomerProfile.objects.create(user=customer)
        messages.warning(request, f"Created a new profile for user {customer.username} as one didn't exist.")

    # Get customer's orders
    orders = Order.objects.filter(user=customer).order_by('-created_at')

    # Calculate statistics
    total_orders = orders.count()
    total_spent = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    context = {
        'customer': customer,
        'customer_profile': customer_profile,
        'orders': orders[:10],  # Show only the 10 most recent orders
        'total_orders': total_orders,
        'total_spent': total_spent,
        'active_section': 'customers'
    }

    return render(request, 'accounts/customer_detail.html', context)

@login_required
@permission_required('ecommerce.manage_customers', raise_exception=True)
def blacklist_customer(request, user_id):
    """Add a customer to the blacklist"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})

    customer = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)

    # Check if customer has a profile, create one if not
    try:
        customer_profile = customer.customer_profile
    except CustomerProfile.DoesNotExist:
        # Create a new customer profile
        customer_profile = CustomerProfile.objects.create(user=customer)
        messages.warning(request, f"Created a new profile for user {customer.username} as one didn't exist.")

    reason = request.POST.get('reason', '')

    # Update customer profile
    customer_profile.is_blacklisted = True
    customer_profile.blacklist_reason = reason
    customer_profile.blacklisted_at = timezone.now()
    customer_profile.blacklisted_by = request.user
    customer_profile.save()

    # Log the activity
    StaffActivity.objects.create(
        staff=request.user,
        action='BLACKLIST_CUSTOMER',
        details=f"Blacklisted customer {customer.username} ({customer.get_full_name()}). Reason: {reason}",
        ip_address=get_client_ip(request)
    )

    messages.success(request, f'Customer {customer.get_full_name()} has been added to the blacklist.')
    return redirect('customer_detail', user_id=user_id)

@login_required
@permission_required('ecommerce.manage_customers', raise_exception=True)
def unblacklist_customer(request, user_id):
    """Remove a customer from the blacklist"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'})

    customer = get_object_or_404(User, id=user_id, is_staff=False, is_superuser=False)

    # Check if customer has a profile, create one if not
    try:
        customer_profile = customer.customer_profile
    except CustomerProfile.DoesNotExist:
        # Create a new customer profile
        customer_profile = CustomerProfile.objects.create(user=customer)
        messages.warning(request, f"Created a new profile for user {customer.username} as one didn't exist.")
        # No need to unblacklist as new profiles are not blacklisted by default
        messages.info(request, f"User {customer.username} is not blacklisted.")
        return redirect('customer_detail', user_id=user_id)

    # Update customer profile
    customer_profile.is_blacklisted = False
    customer_profile.save()

    # Log the activity
    StaffActivity.objects.create(
        staff=request.user,
        action='UNBLACKLIST_CUSTOMER',
        details=f"Removed customer {customer.username} ({customer.get_full_name()}) from blacklist.",
        ip_address=get_client_ip(request)
    )

    messages.success(request, f'Customer {customer.get_full_name()} has been removed from the blacklist.')
    return redirect('customer_detail', user_id=user_id)
