from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, F, Avg
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

    # Get inventory alerts
    low_stock_items = MenuItem.objects.filter(
        current_stock__lt=F('stock_alert_threshold'),
        current_stock__gt=0
    ).count()

    out_of_stock_items = MenuItem.objects.filter(current_stock=0).count()

    # Get staff statistics
    active_staff = StaffProfile.objects.filter(is_active_staff=True).count()

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
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'active_staff': active_staff,
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

    # Group by menu item
    item_sales = sales_data.values(
        'menu_item__id',
        'menu_item__name',
        'menu_item__category__name'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum(F('quantity') * F('price')),
        orders=Count('order', distinct=True),
        avg_price=Avg('price')
    ).order_by('-quantity')

    # Calculate totals
    total_quantity = sum(item['quantity'] for item in item_sales)
    total_revenue = sum(item['revenue'] for item in item_sales)

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
    sales_by_day = current_orders.extra(
        select={'day_of_week': "EXTRACT(DOW FROM created_at)"}
    ).values('day_of_week').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('day_of_week')

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
    sales_by_hour = current_orders.extra(
        select={'hour': "EXTRACT(HOUR FROM created_at)"}
    ).values('hour').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('hour')

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
