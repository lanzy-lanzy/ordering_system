from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDate, TruncMonth
from datetime import timedelta, date
import decimal
from .models import MenuItem, InventoryTransaction, PriceHistory, SalesSummary, OrderItem

@login_required
def inventory_dashboard(request):
    """Display inventory dashboard with stock levels and alerts"""
    # Get all menu items with their stock status
    menu_items = MenuItem.objects.all().order_by('category__name', 'name')

    # Get low stock items
    low_stock_items = menu_items.filter(current_stock__lt=F('stock_alert_threshold'), current_stock__gt=0)

    # Get out of stock items
    out_of_stock_items = menu_items.filter(current_stock=0)

    # Get recent inventory transactions
    recent_transactions = InventoryTransaction.objects.select_related('menu_item').order_by('-created_at')[:10]

    # Calculate inventory value
    total_inventory_value = sum(item.current_stock * item.cost_price for item in menu_items)

    context = {
        'menu_items': menu_items,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'recent_transactions': recent_transactions,
        'total_inventory_value': total_inventory_value,
        'active_section': 'inventory'
    }

    return render(request, 'accounts/inventory_dashboard.html', context)

@login_required
def add_inventory(request):
    """Add inventory to a menu item"""
    menu_items = MenuItem.objects.all().order_by('category__name', 'name')

    if request.method == 'POST':
        menu_item_id = request.POST.get('menu_item')
        quantity = request.POST.get('quantity')
        unit_price = request.POST.get('unit_price')
        transaction_type = request.POST.get('transaction_type')
        reference = request.POST.get('reference')
        notes = request.POST.get('notes')

        # Validate data
        if not all([menu_item_id, quantity, transaction_type]):
            messages.error(request, 'Please fill in all required fields')
            return redirect('add_inventory')

        try:
            menu_item = MenuItem.objects.get(id=menu_item_id)
            quantity = int(quantity)

            # For deductions, convert to negative
            if transaction_type in ['SALE', 'WASTE', 'ADJUSTMENT'] and quantity > 0:
                quantity = -quantity

            # Process unit price
            try:
                processed_unit_price = decimal.Decimal(unit_price) if unit_price else None
            except (decimal.InvalidOperation, TypeError):
                processed_unit_price = None

            # Create inventory transaction
            transaction = InventoryTransaction.objects.create(
                menu_item=menu_item,
                transaction_type=transaction_type,
                quantity=quantity,
                unit_price=processed_unit_price,
                reference=reference,
                notes=notes,
                created_by=request.user
            )

            messages.success(request, f'Inventory updated successfully. New stock level: {menu_item.current_stock}')
            return redirect('inventory_dashboard')

        except Exception as e:
            messages.error(request, f'Error updating inventory: {str(e)}')

    context = {
        'menu_items': menu_items,
        'transaction_types': InventoryTransaction.TRANSACTION_TYPES,
        'active_section': 'inventory'
    }

    return render(request, 'accounts/add_inventory.html', context)

@login_required
def inventory_history(request, item_id=None):
    """View inventory history for all items or a specific item"""
    # Get filters
    transaction_type = request.GET.get('transaction_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Base query
    transactions = InventoryTransaction.objects.select_related('menu_item', 'created_by')

    # Apply filters
    if item_id:
        menu_item = get_object_or_404(MenuItem, id=item_id)
        transactions = transactions.filter(menu_item=menu_item)

    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)

    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)

    # Order by most recent
    transactions = transactions.order_by('-created_at')

    context = {
        'transactions': transactions,
        'menu_item': menu_item if item_id else None,
        'transaction_types': InventoryTransaction.TRANSACTION_TYPES,
        'transaction_type': transaction_type,
        'date_from': date_from,
        'date_to': date_to,
        'active_section': 'inventory'
    }

    return render(request, 'accounts/inventory_history.html', context)

@login_required
def sales_dashboard(request):
    """Display sales dashboard with revenue and profit metrics"""
    # Get date range
    today = timezone.now().date()
    date_from = request.GET.get('date_from', (today - timedelta(days=30)).isoformat())
    date_to = request.GET.get('date_to', today.isoformat())

    # Get sales summaries for the period
    sales_summaries = SalesSummary.objects.filter(
        date__gte=date_from,
        date__lte=date_to
    ).select_related('menu_item')

    # Calculate totals
    total_revenue = sales_summaries.aggregate(Sum('revenue'))['revenue__sum'] or 0
    total_cost = sales_summaries.aggregate(Sum('cost'))['cost__sum'] or 0
    total_profit = sales_summaries.aggregate(Sum('profit'))['profit__sum'] or 0
    total_items_sold = sales_summaries.aggregate(Sum('quantity_sold'))['quantity_sold__sum'] or 0

    # Get profit margin
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

    # Get top selling items
    top_items = MenuItem.objects.annotate(
        total_sold=Sum('sales_summaries__quantity_sold', filter=Q(
            sales_summaries__date__gte=date_from,
            sales_summaries__date__lte=date_to
        ))
    ).filter(total_sold__gt=0).order_by('-total_sold')[:10]

    # Get most profitable items
    most_profitable = MenuItem.objects.annotate(
        total_profit=Sum('sales_summaries__profit', filter=Q(
            sales_summaries__date__gte=date_from,
            sales_summaries__date__lte=date_to
        ))
    ).filter(total_profit__gt=0).order_by('-total_profit')[:10]

    # Get daily sales data for chart
    daily_sales = SalesSummary.objects.filter(
        date__gte=date_from,
        date__lte=date_to
    ).values('date').annotate(
        daily_revenue=Sum('revenue'),
        daily_profit=Sum('profit')
    ).order_by('date')

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'total_items_sold': total_items_sold,
        'top_items': top_items,
        'most_profitable': most_profitable,
        'daily_sales': daily_sales,
        'active_section': 'sales'
    }

    return render(request, 'accounts/sales_dashboard.html', context)

@login_required
def price_history(request, item_id=None):
    """View price history for all items or a specific item"""
    # Base query
    history = PriceHistory.objects.select_related('menu_item', 'changed_by')

    # Filter by item if provided
    if item_id:
        menu_item = get_object_or_404(MenuItem, id=item_id)
        history = history.filter(menu_item=menu_item)

    # Order by most recent
    history = history.order_by('-changed_at')

    context = {
        'history': history,
        'menu_item': menu_item if item_id else None,
        'active_section': 'inventory'
    }

    return render(request, 'accounts/price_history.html', context)

@login_required
def item_sales_history(request, item_id):
    """View detailed sales history for a specific item"""
    menu_item = get_object_or_404(MenuItem, id=item_id)

    # Get date range
    today = timezone.now().date()
    date_from = request.GET.get('date_from', (today - timedelta(days=90)).isoformat())
    date_to = request.GET.get('date_to', today.isoformat())

    # Get daily sales data
    daily_sales = SalesSummary.objects.filter(
        menu_item=menu_item,
        date__gte=date_from,
        date__lte=date_to
    ).order_by('date')

    # Get order items for this menu item
    order_items = OrderItem.objects.filter(
        menu_item=menu_item,
        order__created_at__date__gte=date_from,
        order__created_at__date__lte=date_to
    ).select_related('order').order_by('-order__created_at')

    # Calculate totals
    total_quantity = daily_sales.aggregate(Sum('quantity_sold'))['quantity_sold__sum'] or 0
    total_revenue = daily_sales.aggregate(Sum('revenue'))['revenue__sum'] or 0
    total_profit = daily_sales.aggregate(Sum('profit'))['profit__sum'] or 0

    context = {
        'menu_item': menu_item,
        'daily_sales': daily_sales,
        'order_items': order_items,
        'date_from': date_from,
        'date_to': date_to,
        'total_quantity': total_quantity,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'active_section': 'sales'
    }

    return render(request, 'accounts/item_sales_history.html', context)
