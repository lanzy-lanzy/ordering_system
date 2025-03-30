import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncDate, TruncHour, TruncMonth, TruncWeek
from django.utils import timezone
from .models import Order, OrderItem, Category

@login_required
def admin_sales_report(request):
    """Comprehensive sales report for admin with filtering and printing options"""
    # Get date range
    today = timezone.now().date()
    date_from = request.GET.get('date_from', (today - datetime.timedelta(days=30)).isoformat())
    date_to = request.GET.get('date_to', today.isoformat())
    category_id = request.GET.get('category', '')
    report_type = request.GET.get('report_type', 'daily')  # daily, weekly, monthly

    # Base query for completed orders
    orders = Order.objects.filter(
        status='COMPLETED',
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )

    # No payment method filter since it doesn't exist in the Order model

    # Get sales data
    sales_data = OrderItem.objects.filter(
        order__in=orders
    )

    # Apply category filter if provided
    if category_id:
        sales_data = sales_data.filter(menu_item__category_id=category_id)

    # Group by menu item
    item_sales = sales_data.values(
        'menu_item__id',
        'menu_item__name',
        'menu_item__category__name',
        'menu_item__cost_price'
    ).annotate(
        quantity=Sum('quantity'),
        orders=Count('order', distinct=True),
        avg_price=Avg('price')
    )

    # Calculate revenue for each item
    for item in item_sales:
        # Get all order items for this menu item
        item_order_items = sales_data.filter(menu_item__id=item['menu_item__id'])
        # Calculate revenue
        item['revenue'] = sum(oi.quantity * oi.price for oi in item_order_items.iterator())

    # Sort by revenue
    item_sales = sorted(item_sales, key=lambda x: x['revenue'], reverse=True)

    # Calculate profit for each item
    for item in item_sales:
        cost_price = item['menu_item__cost_price'] or 0
        item['cost'] = cost_price * item['quantity']
        item['profit'] = item['revenue'] - item['cost']
        item['profit_margin'] = (item['profit'] / item['revenue'] * 100) if item['revenue'] > 0 else 0

    # Calculate totals
    total_quantity = sum(item['quantity'] for item in item_sales)
    total_revenue = sum(item['revenue'] for item in item_sales)
    total_profit = sum(item['profit'] for item in item_sales)
    total_cost = sum(item['cost'] for item in item_sales)
    overall_profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Get order metrics
    order_count = orders.count()
    avg_order_value = total_revenue / order_count if order_count > 0 else 0

    # Initialize default values in case there's no data
    time_labels = []
    time_values = []
    time_counts = []

    # Time series data based on report type
    if orders.exists():
        if report_type == 'daily':
            time_series = orders.annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('date')

            # Format for chart
            time_labels = [entry['date'].strftime('%b %d') for entry in time_series]
            time_values = [float(entry['total']) for entry in time_series]
            time_counts = [entry['count'] for entry in time_series]

        elif report_type == 'weekly':
            time_series = orders.annotate(
                week=TruncWeek('created_at')
            ).values('week').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('week')

            # Format for chart
            time_labels = [f"Week of {entry['week'].strftime('%b %d')}" for entry in time_series]
            time_values = [float(entry['total']) for entry in time_series]
            time_counts = [entry['count'] for entry in time_series]

        else:  # monthly
            time_series = orders.annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                total=Sum('total_amount'),
                count=Count('id')
            ).order_by('month')

            # Format for chart
            time_labels = [entry['month'].strftime('%b %Y') for entry in time_series]
            time_values = [float(entry['total']) for entry in time_series]
            time_counts = [entry['count'] for entry in time_series]

    # Sales by hour of day
    if orders.exists():
        sales_by_hour = orders.annotate(
            hour=TruncHour('created_at')
        ).values(
            hour_num=F('hour__hour')
        ).annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('hour_num')
    else:
        sales_by_hour = []

    # Format hour data
    hour_data = []
    for i in range(24):
        hour_info = next((h for h in sales_by_hour if h['hour_num'] == i), {'total': 0, 'count': 0})
        hour_data.append({
            'hour': f"{i:02d}:00",
            'total': hour_info['total'] if isinstance(hour_info.get('total'), (int, float)) else 0,
            'count': hour_info['count'] if isinstance(hour_info.get('count'), (int, float)) else 0
        })

    # Sales by category
    category_data = {}
    for item in sales_data.select_related('menu_item', 'menu_item__category'):
        category_name = item.menu_item.category.name if item.menu_item and item.menu_item.category else 'No Category'
        if category_name not in category_data:
            category_data[category_name] = {'revenue': 0, 'quantity': 0}
        category_data[category_name]['revenue'] += item.quantity * item.price
        category_data[category_name]['quantity'] += item.quantity

    # Convert to list for template
    category_sales = [{
        'menu_item__category__name': cat_name,
        'revenue': cat_data['revenue'],
        'quantity': cat_data['quantity']
    } for cat_name, cat_data in category_data.items()]

    # Sort by revenue
    category_sales = sorted(category_sales, key=lambda x: x['revenue'], reverse=True)

    # Get categories for filter
    categories = Category.objects.all()

    # No payment methods filter since it doesn't exist in the Order model
    payment_methods = []

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'category_id': category_id,
        'report_type': report_type,
        'categories': categories,
        'payment_methods': payment_methods,
        'item_sales': item_sales,
        'total_quantity': total_quantity,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'total_cost': total_cost,
        'overall_profit_margin': overall_profit_margin,
        'order_count': order_count,
        'avg_order_value': avg_order_value,
        'time_labels': time_labels,
        'time_values': time_values,
        'time_counts': time_counts,
        'hour_data': hour_data,
        'category_sales': category_sales,
        'active_section': 'sales_report'
    }

    return render(request, 'admin/sales_report.html', context)
