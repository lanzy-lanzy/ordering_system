from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from django.http import JsonResponse
from decimal import Decimal
import datetime

from .models import Order, OrderItem, MenuItem, StaffActivity

@login_required
@permission_required('ecommerce.process_orders', raise_exception=True)
def cashier_dashboard(request):
    """Main dashboard for cashiers"""
    # Get today's date
    today = timezone.now().date()
    
    # Get today's orders
    today_orders = Order.objects.filter(
        created_at__date=today
    ).order_by('-created_at')
    
    # Get pending orders (not completed or cancelled)
    pending_orders = today_orders.filter(
        status__in=['PENDING', 'PROCESSING', 'READY']
    )
    
    # Get completed orders
    completed_orders = today_orders.filter(status='COMPLETED')
    
    # Get cancelled orders
    cancelled_orders = today_orders.filter(status='CANCELLED')
    
    # Calculate today's sales
    today_sales = completed_orders.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Calculate today's order count
    today_order_count = completed_orders.count()
    
    # Calculate average order value
    avg_order_value = today_sales / today_order_count if today_order_count > 0 else 0
    
    # Get most ordered items today
    top_items = OrderItem.objects.filter(
        order__in=completed_orders
    ).values(
        'menu_item__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum(F('quantity') * F('price'))
    ).order_by('-total_quantity')[:5]
    
    # Log activity
    StaffActivity.objects.create(
        staff=request.user,
        action='LOGIN',
        details=f"Accessed cashier dashboard",
        ip_address=get_client_ip(request)
    )
    
    context = {
        'today_date': today,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'today_sales': today_sales,
        'today_order_count': today_order_count,
        'avg_order_value': avg_order_value,
        'top_items': top_items,
        'active_section': 'cashier_dashboard'
    }
    
    return render(request, 'cashier/dashboard.html', context)

@login_required
@permission_required('ecommerce.process_orders', raise_exception=True)
def new_order(request):
    """Create a new order"""
    # Get all menu items
    menu_items = MenuItem.objects.filter(is_available=True).order_by('category__name', 'name')
    
    if request.method == 'POST':
        # Get customer information
        customer_name = request.POST.get('customer_name', '')
        customer_phone = request.POST.get('customer_phone', '')
        order_type = request.POST.get('order_type', 'DINE_IN')
        table_number = request.POST.get('table_number', '')
        special_instructions = request.POST.get('special_instructions', '')
        
        # Get order items
        item_ids = request.POST.getlist('item_id[]')
        quantities = request.POST.getlist('quantity[]')
        special_instructions_list = request.POST.getlist('item_instructions[]')
        
        if not item_ids or not quantities or len(item_ids) != len(quantities):
            messages.error(request, 'Please add at least one item to the order')
            return redirect('new_order')
        
        try:
            # Create order
            order = Order.objects.create(
                customer_name=customer_name,
                customer_phone=customer_phone,
                order_type=order_type,
                table_number=table_number,
                special_instructions=special_instructions,
                status='PENDING',
                created_by=request.user
            )
            
            # Calculate total amount
            total_amount = Decimal('0.00')
            
            # Add order items
            for i in range(len(item_ids)):
                item_id = item_ids[i]
                quantity = int(quantities[i])
                item_instructions = special_instructions_list[i] if i < len(special_instructions_list) else ''
                
                if quantity <= 0:
                    continue
                
                menu_item = MenuItem.objects.get(id=item_id)
                price = menu_item.price
                
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity,
                    price=price,
                    special_instructions=item_instructions
                )
                
                total_amount += price * quantity
            
            # Update order total
            order.total_amount = total_amount
            order.save()
            
            # Log activity
            StaffActivity.objects.create(
                staff=request.user,
                action='CREATE_ORDER',
                details=f"Created new order #{order.id} for {customer_name}",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f'Order #{order.id} created successfully')
            return redirect('view_order', order_id=order.id)
            
        except Exception as e:
            messages.error(request, f'Error creating order: {str(e)}')
    
    context = {
        'menu_items': menu_items,
        'active_section': 'new_order'
    }
    
    return render(request, 'cashier/new_order.html', context)

@login_required
@permission_required('ecommerce.process_orders', raise_exception=True)
def view_order(request, order_id):
    """View order details"""
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.all()
    
    context = {
        'order': order,
        'order_items': order_items,
        'active_section': 'orders'
    }
    
    return render(request, 'cashier/view_order.html', context)

@login_required
@permission_required('ecommerce.process_orders', raise_exception=True)
def update_order_status(request, order_id):
    """Update order status"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    if new_status not in dict(Order.STATUS_CHOICES):
        return JsonResponse({'status': 'error', 'message': 'Invalid status'})
    
    try:
        old_status = order.status
        order.status = new_status
        
        # If completing the order, set completed_at
        if new_status == 'COMPLETED' and not order.completed_at:
            order.completed_at = timezone.now()
        
        order.save()
        
        # Log activity
        StaffActivity.objects.create(
            staff=request.user,
            action='UPDATE_ORDER',
            details=f"Updated order #{order.id} status from {old_status} to {new_status}",
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Order status updated to {dict(Order.STATUS_CHOICES)[new_status]}'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error updating order status: {str(e)}'})

@login_required
@permission_required('ecommerce.process_orders', raise_exception=True)
def orders_list(request):
    """View list of orders with filtering"""
    # Get filters
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', timezone.now().date().isoformat())
    date_to = request.GET.get('date_to', timezone.now().date().isoformat())
    search_query = request.GET.get('q', '')
    
    # Base queryset
    orders = Order.objects.all().order_by('-created_at')
    
    # Apply filters
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(table_number__icontains=search_query)
        )
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'status_choices': Order.STATUS_CHOICES,
        'active_section': 'orders'
    }
    
    return render(request, 'cashier/orders_list.html', context)

@login_required
@permission_required('ecommerce.process_orders', raise_exception=True)
def print_receipt(request, order_id):
    """Generate receipt for printing"""
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.all()
    
    # Log activity
    StaffActivity.objects.create(
        staff=request.user,
        action='OTHER',
        details=f"Printed receipt for order #{order.id}",
        ip_address=get_client_ip(request)
    )
    
    context = {
        'order': order,
        'order_items': order_items,
        'print_date': timezone.now(),
        'cashier_name': request.user.get_full_name()
    }
    
    return render(request, 'cashier/receipt.html', context)

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
