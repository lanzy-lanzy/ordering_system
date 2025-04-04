from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Avg, DecimalField, Value
from django.db.models.expressions import ExpressionWrapper, RawSQL
from django.http import JsonResponse
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
import calendar
from dateutil.relativedelta import relativedelta

from .models import (
    Order, OrderItem, MenuItem, Category, StaffActivity,
    StaffProfile, InventoryTransaction, SalesSummary, PriceHistory,
    Reservation
)

@login_required
def manager_dashboard(request):
    """Main dashboard for managers with overview of restaurant operations"""
    # Get date range for dashboard stats
    today = timezone.now().date()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    # Get sales statistics
    today_sales = Order.objects.filter(
        status='COMPLETED',
        created_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    week_sales = Order.objects.filter(
        status='COMPLETED',
        created_at__date__gte=start_of_week,
        created_at__date__lte=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    month_sales = Order.objects.filter(
        status='COMPLETED',
        created_at__date__gte=start_of_month,
        created_at__date__lte=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Get order statistics
    today_orders = Order.objects.filter(created_at__date=today).count()
    pending_orders = Order.objects.filter(status__in=['PENDING', 'PROCESSING']).count()

    # Get reservation statistics
    pending_reservations = Reservation.objects.filter(status='PENDING').count()

    # Get inventory alerts
    low_stock_items = MenuItem.objects.filter(
        current_stock__lt=F('stock_alert_threshold'),
        current_stock__gt=0
    ).count()

    out_of_stock_items = MenuItem.objects.filter(current_stock=0).count()

    # Get staff statistics
    active_staff = StaffProfile.objects.filter(is_active_staff=True).count()

    # Get cashier sales for today
    cashier_sales = Order.objects.filter(
        status='COMPLETED',
        created_at__date=today,
        created_by__isnull=False
    ).values(
        'created_by__id',
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name'
    ).annotate(
        order_count=Count('id'),
        total_sales=Sum('total_amount')
    ).order_by('-total_sales')[:5]  # Top 5 cashiers

    # Enrich cashier data
    for sale in cashier_sales:
        try:
            cashier = User.objects.get(id=sale['created_by__id'])
            sale['full_name'] = cashier.get_full_name() or cashier.username
        except User.DoesNotExist:
            sale['full_name'] = f"{sale['created_by__first_name']} {sale['created_by__last_name']}".strip() or sale['created_by__username']

    # Get recent activities
    recent_activities = StaffActivity.objects.select_related('staff').order_by('-timestamp')[:10]

    # Get top selling items this month
    top_items = OrderItem.objects.filter(
        order__status='COMPLETED',
        order__created_at__date__gte=start_of_month,
        order__created_at__date__lte=today
    ).values(
        'menu_item__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum(F('quantity') * F('price'))
    ).order_by('-total_quantity')[:5]

    # Get daily sales for the past week for chart
    past_week = today - datetime.timedelta(days=6)
    daily_sales = Order.objects.filter(
        status='COMPLETED',
        created_at__date__gte=past_week,
        created_at__date__lte=today
    ).values(
        'created_at__date'
    ).annotate(
        date=F('created_at__date'),
        total=Sum('total_amount')
    ).order_by('date')

    # Format dates for chart
    chart_labels = []
    chart_data = []

    for i in range(7):
        date = past_week + datetime.timedelta(days=i)
        chart_labels.append(date.strftime('%a'))

        # Find sales for this date
        day_sale = next((item['total'] for item in daily_sales if item['date'] == date), 0)
        chart_data.append(float(day_sale))

    # Log activity
    StaffActivity.objects.create(
        staff=request.user,
        action='LOGIN',
        details=f"Accessed manager dashboard",
        ip_address=get_client_ip(request)
    )

    context = {
        'today_date': today,
        'today_sales': today_sales,
        'week_sales': week_sales,
        'month_sales': month_sales,
        'today_orders': today_orders,
        'pending_orders': pending_orders,
        'pending_reservations': pending_reservations,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'active_staff': active_staff,
        'cashier_sales': cashier_sales,  # Add cashier sales to context
        'recent_activities': recent_activities,
        'top_items': top_items,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'active_section': 'manager_dashboard'
    }

    return render(request, 'manager/dashboard.html', context)

@login_required
def sales_report(request):
    """Detailed sales reports with filtering options"""
    # Get date range
    today = timezone.now().date()
    date_from = request.GET.get('date_from', (today - datetime.timedelta(days=30)).isoformat())
    date_to = request.GET.get('date_to', today.isoformat())
    category_id = request.GET.get('category', '')

    # Get sales data
    sales_data = OrderItem.objects.filter(
        order__status='COMPLETED',
        order__created_at__date__gte=date_from,
        order__created_at__date__lte=date_to
    )

    if category_id:
        sales_data = sales_data.filter(menu_item__category_id=category_id)

    # Use a simpler approach with two separate queries
    # First, get the basic aggregations
    item_sales = []

    # Get unique menu items in the filtered data
    menu_item_ids = sales_data.values_list('menu_item_id', flat=True).distinct()

    for menu_item_id in menu_item_ids:
        # Get menu item details
        menu_item = MenuItem.objects.get(id=menu_item_id)

        # Get order items for this menu item
        item_orders = sales_data.filter(menu_item_id=menu_item_id)

        # Calculate metrics
        quantity = item_orders.aggregate(total=Sum('quantity'))['total'] or 0
        orders_count = item_orders.values('order').distinct().count()
        avg_price = item_orders.aggregate(avg=Avg('price'))['avg'] or 0

        # Calculate revenue manually
        revenue = sum(oi.quantity * oi.price for oi in item_orders)

        # Create item dict
        item = {
            'menu_item__id': menu_item_id,
            'menu_item__name': menu_item.name,
            'menu_item__category__name': menu_item.category.name if menu_item.category else 'No Category',
            'quantity': quantity,
            'revenue': revenue,
            'orders': orders_count,
            'avg_price': avg_price
        }

        item_sales.append(item)

    # Sort by quantity
    item_sales = sorted(item_sales, key=lambda x: x['quantity'], reverse=True)

    # Calculate totals
    total_quantity = sum(item['quantity'] or 0 for item in item_sales)
    total_revenue = sum(item['revenue'] or 0 for item in item_sales)

    # Get categories for filter
    categories = Category.objects.all()

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'category_id': category_id,
        'categories': categories,
        'item_sales': item_sales,
        'total_quantity': total_quantity,
        'total_revenue': total_revenue,
        'active_section': 'sales_report'
    }

    return render(request, 'manager/sales_report.html', context)

@login_required
def inventory_overview(request):
    """Overview of inventory status and value"""
    # Get all menu items with their inventory status
    menu_items = MenuItem.objects.all().select_related('category').order_by('category__name', 'name')

    # Get low stock and out of stock items
    low_stock_items = menu_items.filter(
        current_stock__lt=F('stock_alert_threshold'),
        current_stock__gt=0
    )

    out_of_stock_items = menu_items.filter(current_stock=0)

    # Calculate inventory value
    total_inventory_value = sum(item.current_stock * item.cost_price for item in menu_items)

    # Get recent inventory transactions
    recent_transactions = InventoryTransaction.objects.select_related(
        'menu_item', 'created_by'
    ).order_by('-created_at')[:10]

    # Get inventory value by category
    categories = Category.objects.all()
    category_values = []

    for category in categories:
        items = menu_items.filter(category=category)
        value = sum(item.current_stock * item.cost_price for item in items)
        if value > 0:
            category_values.append({
                'name': category.name,
                'value': value
            })

    context = {
        'menu_items': menu_items,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'total_inventory_value': total_inventory_value,
        'recent_transactions': recent_transactions,
        'category_values': category_values,
        'active_section': 'inventory_overview'
    }

    return render(request, 'manager/inventory_overview.html', context)

@login_required
def staff_overview(request):
    """Overview of staff performance and activity"""
    # Get all staff members
    staff_members = User.objects.filter(
        staff_profile__isnull=False,
        staff_profile__is_active_staff=True
    ).select_related('staff_profile')

    # Get date range
    today = timezone.now().date()
    date_from = request.GET.get('date_from', (today - datetime.timedelta(days=30)).isoformat())
    date_to = request.GET.get('date_to', today.isoformat())

    # Get staff activities
    activities = StaffActivity.objects.filter(
        timestamp__date__gte=date_from,
        timestamp__date__lte=date_to
    ).values('staff__id').annotate(
        login_count=Count('id', filter=Q(action='LOGIN')),
        order_count=Count('id', filter=Q(action='CREATE_ORDER')),
        total_activities=Count('id')
    )

    # Get orders created by staff
    orders = Order.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        created_by__isnull=False
    ).values('created_by').annotate(
        order_count=Count('id'),
        total_sales=Sum('total_amount')
    )

    # Combine data
    staff_data = []
    for member in staff_members:
        # Find activity data
        activity_data = next((a for a in activities if a['staff__id'] == member.id), {
            'login_count': 0,
            'order_count': 0,
            'total_activities': 0
        })

        # Find order data
        order_data = next((o for o in orders if o['created_by'] == member.id), {
            'order_count': 0,
            'total_sales': 0
        })

        staff_data.append({
            'user': member,
            'profile': member.staff_profile,
            'login_count': activity_data['login_count'],
            'order_count': order_data['order_count'],
            'total_sales': order_data['total_sales'] or 0,
            'total_activities': activity_data['total_activities']
        })

    # Sort by total sales
    staff_data.sort(key=lambda x: x['total_sales'], reverse=True)

    context = {
        'staff_data': staff_data,
        'date_from': date_from,
        'date_to': date_to,
        'active_section': 'staff_overview'
    }

    return render(request, 'manager/staff_overview.html', context)

@login_required
def performance_metrics(request):
    """Advanced performance metrics and KPIs"""
    # Get date range
    today = timezone.now().date()

    # Default to current month
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + relativedelta(months=1) - datetime.timedelta(days=1))

    date_from = request.GET.get('date_from', start_of_month.isoformat())
    date_to = request.GET.get('date_to', end_of_month.isoformat())

    # Get comparison period (previous month by default)
    prev_start = (datetime.datetime.strptime(date_from, '%Y-%m-%d').date() - relativedelta(months=1))
    prev_end = (datetime.datetime.strptime(date_to, '%Y-%m-%d').date() - relativedelta(months=1))

    # Get current period metrics
    current_orders = Order.objects.filter(
        status='COMPLETED',
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )

    current_metrics = {
        'total_sales': current_orders.aggregate(total=Sum('total_amount'))['total'] or 0,
        'order_count': current_orders.count(),
        'avg_order_value': 0
    }

    if current_metrics['order_count'] > 0:
        current_metrics['avg_order_value'] = current_metrics['total_sales'] / current_metrics['order_count']

    # Get previous period metrics
    prev_orders = Order.objects.filter(
        status='COMPLETED',
        created_at__date__gte=prev_start,
        created_at__date__lte=prev_end
    )

    prev_metrics = {
        'total_sales': prev_orders.aggregate(total=Sum('total_amount'))['total'] or 0,
        'order_count': prev_orders.count(),
        'avg_order_value': 0
    }

    if prev_metrics['order_count'] > 0:
        prev_metrics['avg_order_value'] = prev_metrics['total_sales'] / prev_metrics['order_count']

    # Calculate changes
    changes = {
        'sales_change': calculate_percentage_change(prev_metrics['total_sales'], current_metrics['total_sales']),
        'order_change': calculate_percentage_change(prev_metrics['order_count'], current_metrics['order_count']),
        'aov_change': calculate_percentage_change(prev_metrics['avg_order_value'], current_metrics['avg_order_value'])
    }

    # Get sales by day of week
    # Use annotate with functions that work in SQLite
    sales_by_day = []
    for i in range(7):
        # Filter orders for each day of the week
        day_orders = current_orders.filter(created_at__week_day=i+1)  # Django uses 1-7 for week_day
        if day_orders.exists():
            sales_by_day.append({
                'day_of_week': i,  # Convert to 0-6 format for our display
                'total': day_orders.aggregate(total=Sum('total_amount'))['total'] or 0,
                'count': day_orders.count()
            })

    # Format day of week data
    days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    day_data = []

    for i in range(7):
        day_info = next((d for d in sales_by_day if d['day_of_week'] == i), {'total': 0, 'count': 0})
        day_data.append({
            'name': days_of_week[i],
            'total': day_info['total'] or 0,
            'count': day_info['count'] or 0
        })

    # Get sales by hour
    # Use a more compatible approach for SQLite
    sales_by_hour = []
    for i in range(24):
        # Filter orders for each hour
        hour_orders = current_orders.filter(created_at__hour=i)
        if hour_orders.exists():
            sales_by_hour.append({
                'hour': i,
                'total': hour_orders.aggregate(total=Sum('total_amount'))['total'] or 0,
                'count': hour_orders.count()
            })

    # Format hour data
    hour_data = []
    for i in range(24):
        hour_info = next((h for h in sales_by_hour if h['hour'] == i), {'total': 0, 'count': 0})
        hour_data.append({
            'hour': f"{i}:00",
            'total': hour_info['total'] or 0,
            'count': hour_info['count'] or 0
        })

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'current_metrics': current_metrics,
        'prev_metrics': prev_metrics,
        'changes': changes,
        'day_data': day_data,
        'hour_data': hour_data,
        'active_section': 'performance_metrics'
    }

    return render(request, 'manager/performance_metrics.html', context)


@login_required
def reservations_dashboard(request):
    """Reservations dashboard for managers"""
    today = timezone.now().date()

    # Get reservations statistics
    total_reservations = Reservation.objects.count()
    pending_reservations = Reservation.objects.filter(status='PENDING').count()
    confirmed_reservations = Reservation.objects.filter(status='CONFIRMED').count()
    cancelled_reservations = Reservation.objects.filter(status='CANCELLED').count()

    # Today's reservations
    today_reservations = Reservation.objects.filter(date=today).order_by('time')
    today_pending = today_reservations.filter(status='PENDING').count()
    today_confirmed = today_reservations.filter(status='CONFIRMED').count()

    # Upcoming reservations (next 7 days)
    next_week = today + datetime.timedelta(days=7)
    upcoming_reservations = Reservation.objects.filter(
        date__gt=today,
        date__lte=next_week
    ).order_by('date', 'time')

    # Filter reservations based on query parameters
    reservations = Reservation.objects.all().order_by('-date', '-time')

    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        reservations = reservations.filter(status=status_filter)

    # Filter by date range if provided
    date_filter = request.GET.get('date', 'upcoming')

    if date_filter == 'today':
        reservations = reservations.filter(date=today)
    elif date_filter == 'upcoming':
        reservations = reservations.filter(date__gte=today)
    elif date_filter == 'past':
        reservations = reservations.filter(date__lt=today)
    elif date_filter == 'next_week':
        reservations = reservations.filter(date__gt=today, date__lte=next_week)

    # Update reservation status if form submitted
    if request.method == 'POST':
        reservation_id = request.POST.get('reservation_id')
        new_status = request.POST.get('status')

        if reservation_id and new_status in dict(Reservation.STATUS_CHOICES):
            reservation = get_object_or_404(Reservation, id=reservation_id)
            reservation.status = new_status
            reservation.save()

            # Log the activity
            StaffActivity.objects.create(
                staff=request.user,
                action='UPDATE_RESERVATION',
                details=f"Updated reservation #{reservation_id} status to {dict(Reservation.STATUS_CHOICES)[new_status]}"
            )

            messages.success(request, f'Reservation #{reservation_id} status updated to {dict(Reservation.STATUS_CHOICES)[new_status]}')
            return redirect('reservations_dashboard')

    # Group reservations by date for calendar view
    calendar_data = {}
    for res in upcoming_reservations:
        date_str = res.date.strftime('%Y-%m-%d')
        if date_str not in calendar_data:
            calendar_data[date_str] = {
                'date': res.date,
                'total': 0,
                'pending': 0,
                'confirmed': 0,
                'cancelled': 0
            }

        calendar_data[date_str]['total'] += 1
        if res.status == 'PENDING':
            calendar_data[date_str]['pending'] += 1
        elif res.status == 'CONFIRMED':
            calendar_data[date_str]['confirmed'] += 1
        elif res.status == 'CANCELLED':
            calendar_data[date_str]['cancelled'] += 1

    context = {
        'total_reservations': total_reservations,
        'pending_reservations': pending_reservations,
        'confirmed_reservations': confirmed_reservations,
        'cancelled_reservations': cancelled_reservations,
        'today_reservations': today_reservations,
        'today_pending': today_pending,
        'today_confirmed': today_confirmed,
        'upcoming_reservations': upcoming_reservations,
        'reservations': reservations,
        'status_filter': status_filter or 'all',
        'date_filter': date_filter,
        'status_choices': Reservation.STATUS_CHOICES,
        'calendar_data': calendar_data,
        'today': today,
        'active_section': 'reservations_dashboard'
    }

    return render(request, 'manager/reservations_dashboard.html', context)

@login_required
def cashier_sales_report(request):
    """Sales report filtered by cashier"""
    # Get date range
    today = timezone.now().date()
    date_from = request.GET.get('date_from', (today - datetime.timedelta(days=30)).isoformat())
    date_to = request.GET.get('date_to', today.isoformat())
    cashier_id = request.GET.get('cashier', '')

    # Get all cashiers (users with staff profile and CASHIER role)
    cashiers = User.objects.filter(
        staff_profile__isnull=False,
        staff_profile__role='CASHIER',
        staff_profile__is_active_staff=True
    ).select_related('staff_profile')

    # Get completed orders within date range
    orders_query = Order.objects.filter(
        status='COMPLETED',
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        created_by__isnull=False
    )

    # Filter by specific cashier if selected
    if cashier_id:
        orders_query = orders_query.filter(created_by_id=cashier_id)

    # Get sales data by cashier
    cashier_sales = orders_query.values(
        'created_by__id',
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name'
    ).annotate(
        order_count=Count('id'),
        total_sales=Sum('total_amount'),
        avg_order_value=Avg('total_amount')
    ).order_by('-total_sales')

    # Enrich data with additional cashier information
    for sale in cashier_sales:
        # Get the cashier user object
        try:
            cashier = User.objects.get(id=sale['created_by__id'])
            sale['full_name'] = cashier.get_full_name() or cashier.username
            sale['role'] = cashier.staff_profile.get_role_display() if hasattr(cashier, 'staff_profile') else 'Unknown'
            sale['employee_id'] = cashier.staff_profile.employee_id if hasattr(cashier, 'staff_profile') else ''
        except User.DoesNotExist:
            sale['full_name'] = f"{sale['created_by__first_name']} {sale['created_by__last_name']}".strip() or sale['created_by__username']
            sale['role'] = 'Unknown'
            sale['employee_id'] = ''

    # Get daily sales data for selected cashier or all cashiers
    daily_sales = []
    date_range = []
    current_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()

    while current_date <= end_date:
        date_range.append(current_date)
        current_date += datetime.timedelta(days=1)

    # Get daily sales for chart
    if cashier_id:
        # For a specific cashier
        for day in date_range:
            day_sales = orders_query.filter(
                created_by_id=cashier_id,
                created_at__date=day
            ).aggregate(
                total=Sum('total_amount'),
                count=Count('id')
            )
            daily_sales.append({
                'date': day,
                'total': day_sales['total'] or 0,
                'count': day_sales['count'] or 0
            })
    else:
        # For all cashiers combined
        for day in date_range:
            day_sales = orders_query.filter(
                created_at__date=day
            ).aggregate(
                total=Sum('total_amount'),
                count=Count('id')
            )
            daily_sales.append({
                'date': day,
                'total': day_sales['total'] or 0,
                'count': day_sales['count'] or 0
            })

    # Calculate totals
    total_orders = sum(sale['order_count'] for sale in cashier_sales)
    total_revenue = sum(sale['total_sales'] or 0 for sale in cashier_sales)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

    # Format data for charts
    chart_labels = [day['date'].strftime('%b %d') for day in daily_sales]
    chart_data = [float(day['total']) for day in daily_sales]
    order_counts = [day['count'] for day in daily_sales]

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'cashier_id': cashier_id,
        'cashiers': cashiers,
        'cashier_sales': cashier_sales,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'order_counts': order_counts,
        'active_section': 'cashier_sales_report'
    }

    return render(request, 'manager/cashier_sales_report.html', context)

def calculate_percentage_change(old_value, new_value):
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 100 if new_value > 0 else 0

    return ((new_value - old_value) / old_value) * 100

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
