from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, F, Q
from django.http import JsonResponse, HttpResponseRedirect
from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Order, OrderItem, MenuItem, StaffActivity, Payment, Refund, Reservation, Category, ReservationPayment

@login_required
def cashier_dashboard(request):
    # Check if user has cashier role
    if hasattr(request.user, 'staff_profile') and request.user.staff_profile.role == 'CASHIER':
        # Grant the permission if the user has the cashier role
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from .models import StaffProfile

        # Try to get the permission
        try:
            content_type = ContentType.objects.get_for_model(StaffProfile)
            perm = Permission.objects.get(codename='process_orders', content_type=content_type)
            # Add the permission to the user
            request.user.user_permissions.add(perm)
            request.user.save()
            print(f"Added process_orders permission to user {request.user.username}")
        except Exception as e:
            print(f"Error adding permission: {str(e)}")
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

    # Get unprocessed reservations
    unprocessed_reservations = Reservation.objects.filter(
        status='CONFIRMED',
        date=today,
        is_processed=False
    ).order_by('time')

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

    # Get pending payments
    pending_payments = Payment.objects.filter(
        status='PENDING'
    ).order_by('-payment_date')[:5]

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
        'unprocessed_reservations': unprocessed_reservations,
        'today_sales': today_sales,
        'today_order_count': today_order_count,
        'avg_order_value': avg_order_value,
        'top_items': top_items,
        'pending_payments': pending_payments,
        'unprocessed_reservations_count': unprocessed_reservations.count(),
        'active_section': 'cashier_dashboard'
    }

    return render(request, 'cashier/dashboard.html', context)

@login_required
def new_order(request):
    """Create a new order"""
    # Get all menu items
    menu_items = MenuItem.objects.filter(is_available=True).order_by('category__name', 'name')

    # Get servers for dine-in orders
    servers = User.objects.filter(staff_profile__role__in=['WAITER', 'CASHIER']).order_by('first_name')

    if request.method == 'POST':
        # Get customer information
        customer_name = request.POST.get('customer_name', '')
        customer_phone = request.POST.get('customer_phone', '')
        order_type = request.POST.get('order_type', 'DINE_IN')
        table_number = request.POST.get('table_number', '')
        special_instructions = request.POST.get('special_instructions', '')

        # Get dine-in specific information
        number_of_guests = request.POST.get('number_of_guests', 1)
        server_assigned_id = request.POST.get('server_assigned', None)
        estimated_dining_time = request.POST.get('estimated_dining_time', 60)
        cash_on_hand = request.POST.get('cash_on_hand', '0')

        # Get split bill information
        split_bill = request.POST.get('split_bill', 'false').lower() == 'true'
        split_type = request.POST.get('split_type', 'equal')
        split_ways = request.POST.get('split_ways', 2)

        # Get order items
        item_ids = request.POST.getlist('item_id[]')
        quantities = request.POST.getlist('quantity[]')
        special_instructions_list = request.POST.getlist('item_instructions[]')

        if not item_ids or not quantities or len(item_ids) != len(quantities):
            messages.error(request, 'Please add at least one item to the order')
            return redirect('new_order')

        try:
            # Calculate total amount first
            total_amount = Decimal('0.00')

            # Get menu items and calculate total
            for i in range(len(item_ids)):
                item_id = item_ids[i]
                quantity = int(quantities[i])

                if quantity <= 0:
                    continue

                menu_item = MenuItem.objects.get(id=item_id)
                price = menu_item.price
                total_amount += price * quantity

            # Set default payment status and order status based on order type
            payment_status = 'PAID' if order_type == 'DINE_IN' else 'PENDING'
            payment_method = 'CASH_ON_HAND' if order_type == 'DINE_IN' else 'PENDING'
            order_status = 'PREPARING' if order_type == 'DINE_IN' else 'PENDING'

            # Create order with basic information including total_amount
            order = Order.objects.create(
                user=request.user,
                customer_name=customer_name,
                customer_phone=customer_phone,
                order_type=order_type,
                table_number=table_number,
                special_instructions=special_instructions,
                status=order_status,  # Set status based on order type
                created_by=request.user,
                total_amount=total_amount,  # Set the total amount here
                payment_status=payment_status,  # Set payment status based on order type
                payment_method=payment_method,  # Set payment method for dine-in
                preparing_at=timezone.now() if order_type == 'DINE_IN' else None  # Set preparing timestamp for dine-in
            )

            # Add dine-in specific information if applicable
            if order_type == 'DINE_IN':
                try:
                    order.number_of_guests = int(number_of_guests)
                except (ValueError, TypeError):
                    order.number_of_guests = 1

                try:
                    order.estimated_dining_time = int(estimated_dining_time)
                except (ValueError, TypeError):
                    order.estimated_dining_time = 60

                if server_assigned_id:
                    try:
                        server = User.objects.get(id=server_assigned_id)
                        order.server_assigned = server
                    except User.DoesNotExist:
                        pass

                # Save split bill information
                order.split_bill = split_bill
                order.split_type = split_type.upper()

                try:
                    order.split_ways = int(split_ways)
                    if order.split_ways < 2:
                        order.split_ways = 2
                except (ValueError, TypeError):
                    order.split_ways = 2

                # Save the order with the updated dine-in fields
                order.save()

                # Create a payment record for dine-in orders
                try:
                    cash_amount = Decimal(cash_on_hand)
                    change_amount = cash_amount - total_amount if cash_amount > total_amount else Decimal('0.00')

                    # Save cash and change amounts to the order
                    order.cash_on_hand = cash_amount
                    order.change_amount = change_amount
                    order.save()

                    payment_notes = f'Cash payment: ₱{cash_amount}. Change: ₱{change_amount}'

                    Payment.objects.create(
                        order=order,
                        amount=total_amount,
                        payment_method='CASH_ON_HAND',
                        status='COMPLETED',
                        verified_by=request.user,
                        verification_date=timezone.now(),
                        reference_number=f'CASH-{order.id}',
                        notes=payment_notes
                    )
                except (ValueError, InvalidOperation):
                    # Fallback if cash_on_hand is not a valid decimal
                    Payment.objects.create(
                        order=order,
                        amount=total_amount,
                        payment_method='CASH_ON_HAND',
                        status='COMPLETED',
                        verified_by=request.user,
                        verification_date=timezone.now(),
                        notes='Automatic payment record for dine-in order'
                    )

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

            # Log activity
            StaffActivity.objects.create(
                staff=request.user,
                action='CREATE_ORDER',
                details=f"Created new order #{order.id} for {customer_name}",
                ip_address=get_client_ip(request)
            )

            # Show success message with change information for dine-in orders
            if order_type == 'DINE_IN':
                try:
                    cash_amount = Decimal(cash_on_hand)
                    change_amount = cash_amount - total_amount if cash_amount > total_amount else Decimal('0.00')
                    if change_amount > 0:
                        messages.success(request, f'Order #{order.id} created successfully. Change: ₱{change_amount:.2f}')
                    else:
                        messages.success(request, f'Order #{order.id} created successfully')
                except (ValueError, InvalidOperation):
                    messages.success(request, f'Order #{order.id} created successfully')
            else:
                messages.success(request, f'Order #{order.id} created successfully')
            return redirect('view_order', order_id=order.id)

        except Exception as e:
            messages.error(request, f'Error creating order: {str(e)}')

    context = {
        'menu_items': menu_items,
        'servers': servers,
        'active_section': 'new_order'
    }

    return render(request, 'cashier/new_order.html', context)

@login_required
def view_order(request, order_id):
    """View order details"""
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.all()

    # Get payment information if available
    payment = Payment.objects.filter(order=order).first()

    context = {
        'order': order,
        'order_items': order_items,
        'payment': payment,
        'active_section': 'orders'
    }

    return render(request, 'cashier/view_order.html', context)

@login_required
def update_prep_time(request, order_id):
    """Update the estimated preparation time for an order"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    order = get_object_or_404(Order, id=order_id)

    # Only allow updating preparation time for orders in PREPARING status
    if order.status != 'PREPARING':
        return JsonResponse({'status': 'error', 'message': 'Can only update preparation time for orders in PREPARING status'})

    try:
        # Get the new preparation time
        prep_time = int(request.POST.get('prep_time', 30))

        # Validate the preparation time (between 5 and 120 minutes)
        if prep_time < 5 or prep_time > 120:
            return JsonResponse({'status': 'error', 'message': 'Preparation time must be between 5 and 120 minutes'})

        # Update the preparation time
        order.estimated_preparation_time = prep_time
        order.save()

        # Log activity
        StaffActivity.objects.create(
            staff=request.user,
            action='UPDATE_ORDER',
            details=f"Updated preparation time for order #{order.id} to {prep_time} minutes",
            ip_address=get_client_ip(request)
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Preparation time updated to {prep_time} minutes'
        })
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid preparation time'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error updating preparation time: {str(e)}'})

@login_required
def update_order_status(request, order_id):
    """Update order status with proper flow validation"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    old_status = order.status

    # Validate the status exists
    if new_status not in dict(Order.STATUS_CHOICES):
        return JsonResponse({'status': 'error', 'message': 'Invalid status'})

    # Validate proper status flow
    valid_transitions = {
        'PENDING': ['PREPARING', 'CANCELLED'],
        'PREPARING': ['READY', 'CANCELLED'],
        'READY': ['COMPLETED', 'CANCELLED'],
        'COMPLETED': [],  # Terminal state
        'CANCELLED': []   # Terminal state
    }

    if new_status not in valid_transitions[old_status]:
        return JsonResponse({
            'status': 'error',
            'message': f'Cannot change order status from {dict(Order.STATUS_CHOICES)[old_status]} to {dict(Order.STATUS_CHOICES)[new_status]}'
        })

    try:
        # Update the status
        order.status = new_status

        # Set timestamps based on status
        if new_status == 'PREPARING':
            order.preparing_at = timezone.now()

            # Set estimated preparation time based on order complexity
            # Default is 30 minutes, but we can adjust based on number of items or item types
            item_count = order.order_items.count()
            if item_count <= 2:
                order.estimated_preparation_time = 15  # Quick orders
            elif item_count <= 5:
                order.estimated_preparation_time = 30  # Standard orders
            else:
                order.estimated_preparation_time = 45  # Complex orders

        elif new_status == 'READY':
            order.ready_at = timezone.now()
        elif new_status == 'COMPLETED':
            order.completed_at = timezone.now()
        elif new_status == 'CANCELLED':
            order.cancelled_at = timezone.now()

        order.save()

        # Log activity with detailed message
        status_messages = {
            'PREPARING': 'started preparing',
            'READY': 'marked as ready for pickup/service',
            'COMPLETED': 'completed',
            'CANCELLED': 'cancelled'
        }

        activity_message = f"Order #{order.id} {status_messages[new_status]}"

        StaffActivity.objects.create(
            staff=request.user,
            action='UPDATE_ORDER',
            details=activity_message,
            ip_address=get_client_ip(request)
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Order status updated to {dict(Order.STATUS_CHOICES)[new_status]}'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error updating order status: {str(e)}'})

@login_required
def orders_list(request):
    """View list of orders with filtering and batch actions"""
    # Handle POST requests for batch actions
    if request.method == 'POST':
        selected_orders = request.POST.getlist('selected_orders')
        action = request.POST.get('action', '')

        if selected_orders and action:
            if action.startswith('update_status_'):
                status = action.replace('update_status_', '')
                if status in dict(Order.STATUS_CHOICES):
                    # Update status for all selected orders
                    updated_count = 0
                    for order_id in selected_orders:
                        try:
                            order = Order.objects.get(id=order_id)
                            old_status = order.status

                            # Check if transition is valid
                            valid_transitions = {
                                'PENDING': ['PREPARING', 'CANCELLED'],
                                'PREPARING': ['READY', 'CANCELLED'],
                                'READY': ['COMPLETED', 'CANCELLED'],
                                'COMPLETED': [],  # Terminal state
                                'CANCELLED': []   # Terminal state
                            }

                            if status in valid_transitions[old_status]:
                                # Update the status
                                order.status = status

                                # Set timestamps based on status
                                if status == 'PREPARING':
                                    order.preparing_at = timezone.now()
                                elif status == 'READY':
                                    order.ready_at = timezone.now()
                                elif status == 'COMPLETED':
                                    order.completed_at = timezone.now()
                                elif status == 'CANCELLED':
                                    order.cancelled_at = timezone.now()

                                order.save()
                                updated_count += 1

                                # Log activity
                                StaffActivity.objects.create(
                                    staff=request.user,
                                    action='UPDATE_ORDER',
                                    details=f"Updated order #{order.id} status to {dict(Order.STATUS_CHOICES)[status]}",
                                    ip_address=get_client_ip(request)
                                )
                        except Order.DoesNotExist:
                            continue
                        except Exception as e:
                            messages.error(request, f"Error updating order #{order_id}: {str(e)}")

                    if updated_count > 0:
                        messages.success(request, f"Successfully updated {updated_count} order(s) to {dict(Order.STATUS_CHOICES)[status]}")

            elif action == 'print_receipts':
                # Redirect to a page that will print multiple receipts
                order_ids = ','.join(selected_orders)
                return redirect(f"/cashier/print-multiple-receipts/?order_ids={order_ids}")

    # Get filters
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', timezone.now().date().isoformat())
    date_to = request.GET.get('date_to', timezone.now().date().isoformat())
    search_query = request.GET.get('q', '')
    order_type_filter = request.GET.get('order_type', '')
    payment_status_filter = request.GET.get('payment_status', '')
    payment_method_filter = request.GET.get('payment_method', '')
    min_amount = request.GET.get('min_amount', '')
    max_amount = request.GET.get('max_amount', '')
    sort_by = request.GET.get('sort', 'newest')

    # Base queryset
    orders = Order.objects.all()

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

    if order_type_filter:
        orders = orders.filter(order_type=order_type_filter)

    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)

    if payment_method_filter:
        orders = orders.filter(payment_method=payment_method_filter)

    if min_amount:
        try:
            orders = orders.filter(total_amount__gte=Decimal(min_amount))
        except (ValueError, TypeError, InvalidOperation):
            pass

    if max_amount:
        try:
            orders = orders.filter(total_amount__lte=Decimal(max_amount))
        except (ValueError, TypeError, InvalidOperation):
            pass

    # Apply sorting
    if sort_by == 'oldest':
        orders = orders.order_by('created_at')
    elif sort_by == 'highest':
        orders = orders.order_by('-total_amount')
    elif sort_by == 'lowest':
        orders = orders.order_by('total_amount')
    else:  # newest
        orders = orders.order_by('-created_at')

    # Log activity
    StaffActivity.objects.create(
        staff=request.user,
        action='VIEW_ORDERS',
        details=f"Viewed orders list with {orders.count()} results",
        ip_address=get_client_ip(request)
    )

    context = {
        'orders': orders,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'order_type_filter': order_type_filter,
        'payment_status_filter': payment_status_filter,
        'payment_method_filter': payment_method_filter,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'sort_by': sort_by,
        'status_choices': Order.STATUS_CHOICES,
        'active_section': 'orders'
    }

    return render(request, 'cashier/orders_list.html', context)

@login_required
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


@login_required
def print_multiple_receipts(request):
    """Print multiple receipts at once"""
    order_ids = request.GET.get('order_ids', '')

    if not order_ids:
        messages.error(request, 'No orders selected for printing')
        return redirect('cashier_orders_list')

    try:
        # Split the comma-separated list of order IDs
        order_id_list = [int(id) for id in order_ids.split(',')]

        # Get all the orders
        orders = Order.objects.filter(id__in=order_id_list)

        if not orders.exists():
            messages.error(request, 'No valid orders found for printing')
            return redirect('cashier_orders_list')

        # Log activity
        StaffActivity.objects.create(
            staff=request.user,
            action='OTHER',
            details=f"Printed multiple receipts for orders: {order_ids}",
            ip_address=get_client_ip(request)
        )

        context = {
            'orders': orders,
            'print_date': timezone.now(),
            'cashier_name': request.user.get_full_name()
        }

        return render(request, 'cashier/multiple_receipts.html', context)

    except Exception as e:
        messages.error(request, f'Error printing receipts: {str(e)}')
        return redirect('cashier_orders_list')

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def pending_payments(request):
    """View and manage pending GCash payments"""
    # Get filters
    status_filter = request.GET.get('status', 'PENDING')
    date_from = request.GET.get('date_from', timezone.now().date().isoformat())
    date_to = request.GET.get('date_to', timezone.now().date().isoformat())

    # Base queryset
    payments = Payment.objects.all().order_by('-payment_date')

    # Apply filters
    if status_filter and status_filter != 'all':
        payments = payments.filter(status=status_filter)

    if date_from:
        payments = payments.filter(payment_date__date__gte=date_from)

    if date_to:
        payments = payments.filter(payment_date__date__lte=date_to)

    # Log activity
    StaffActivity.objects.create(
        staff=request.user,
        action='OTHER',
        details=f"Viewed pending payments",
        ip_address=get_client_ip(request)
    )

    context = {
        'payments': payments,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'active_section': 'payments'
    }

    return render(request, 'cashier/pending_payments.html', context)


@login_required
def view_payment(request, payment_id):
    """View payment details"""
    payment = get_object_or_404(Payment, id=payment_id)

    # Log activity
    StaffActivity.objects.create(
        staff=request.user,
        action='OTHER',
        details=f"Viewed payment #{payment.id} details",
        ip_address=get_client_ip(request)
    )

    context = {
        'payment': payment,
        'active_section': 'payments'
    }

    return render(request, 'cashier/view_payment.html', context)


@login_required
def verify_payment(request, payment_id):
    """Verify a payment as completed"""
    payment = get_object_or_404(Payment, id=payment_id)

    if payment.status != 'PENDING':
        messages.error(request, f'Payment #{payment.id} is already {payment.get_status_display().lower()}')
        return redirect('view_payment', payment_id=payment.id)

    if request.method == 'POST':
        notes = request.POST.get('notes', '')

        # Update payment status
        payment.status = 'COMPLETED'
        payment.verification_date = timezone.now()
        payment.verified_by = request.user
        payment.notes = notes
        payment.save()

        # Update order status
        order = payment.order
        order.payment_status = 'PAID'
        order.status = 'PREPARING'  # Move to preparing status
        order.save()

        # Log activity
        StaffActivity.objects.create(
            staff=request.user,
            action='UPDATE_PAYMENT',
            details=f"Verified payment #{payment.id} for order #{order.id}",
            ip_address=get_client_ip(request)
        )

        messages.success(request, f'Payment #{payment.id} has been verified successfully')
        return redirect('pending_payments')

    context = {
        'payment': payment,
        'active_section': 'payments'
    }

    return render(request, 'cashier/verify_payment.html', context)


@login_required
def record_payment(request, order_id):
    """Record a new payment for an order"""
    order = get_object_or_404(Order, id=order_id)

    if order.payment_status == 'PAID':
        messages.warning(request, f'Order #{order.id} is already marked as paid')
        return redirect('view_order', order_id=order.id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        amount = request.POST.get('amount')
        reference_number = request.POST.get('reference_number', '')
        notes = request.POST.get('notes', '')

        try:
            # Validate payment method
            if payment_method not in dict(Order.PAYMENT_METHOD_CHOICES):
                raise ValueError('Invalid payment method')

            # Validate amount
            amount_decimal = Decimal(amount)
            if amount_decimal <= 0:
                raise ValueError('Payment amount must be greater than zero')

            # Create payment record
            payment = Payment.objects.create(
                order=order,
                amount=amount_decimal,
                payment_method=payment_method,
                reference_number=reference_number,
                notes=notes,
                status='COMPLETED',  # Mark as completed immediately since cashier is recording it
                verified_by=request.user,
                verification_date=timezone.now()
            )

            # Update order payment status
            order.payment_status = 'PAID'

            # Use CASH_ON_HAND for dine-in cash payments
            if order.order_type == 'DINE_IN' and payment_method == 'CASH':
                order.payment_method = 'CASH_ON_HAND'
            else:
                order.payment_method = payment_method

            # If order is still pending, move it to preparing
            if order.status == 'PENDING':
                order.status = 'PREPARING'
                order.preparing_at = timezone.now()

            order.save()

            # Calculate change if cash payment
            change_amount = Decimal('0.00')
            if payment_method == 'CASH' and amount_decimal > order.total_amount:
                change_amount = amount_decimal - order.total_amount

            # Log activity
            StaffActivity.objects.create(
                staff=request.user,
                action='CREATE_PAYMENT',
                details=f"Recorded {payment.get_payment_method_display()} payment of {amount_decimal} for order #{order.id}",
                ip_address=get_client_ip(request)
            )

            messages.success(request, f'Payment of {amount_decimal} recorded successfully for Order #{order.id}')

            if change_amount > 0:
                messages.info(request, f'Change amount: ₱{change_amount:.2f}')

            return redirect('view_order', order_id=order.id)

        except ValueError as e:
            messages.error(request, f'Error recording payment: {str(e)}')
        except InvalidOperation:
            messages.error(request, 'Invalid amount format')
        except Exception as e:
            messages.error(request, f'Error recording payment: {str(e)}')

    context = {
        'order': order,
        'payment_methods': Order.PAYMENT_METHOD_CHOICES,
        'active_section': 'orders'
    }

    return render(request, 'cashier/record_payment.html', context)


@login_required
def reject_payment(request, payment_id):
    """Reject a payment"""
    payment = get_object_or_404(Payment, id=payment_id)

    if payment.status != 'PENDING':
        messages.error(request, f'Payment #{payment.id} is already {payment.get_status_display().lower()}')
        return redirect('view_payment', payment_id=payment.id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '')

        # Update payment status
        payment.status = 'REJECTED'
        payment.verification_date = timezone.now()
        payment.verified_by = request.user
        payment.notes = reason
        payment.save()

        # Log activity
        StaffActivity.objects.create(
            staff=request.user,
            action='UPDATE_PAYMENT',
            details=f"Rejected payment #{payment.id} for order #{payment.order.id}",
            ip_address=get_client_ip(request)
        )

        messages.success(request, f'Payment #{payment.id} has been rejected')
        return redirect('pending_payments')

    context = {
        'payment': payment,
        'active_section': 'payments'
    }

    return render(request, 'cashier/reject_payment.html', context)


@login_required
def cancel_order(request, order_id):
    """Cancel an order and handle all related processes"""
    order = get_object_or_404(Order, id=order_id)

    # Check if order can be cancelled (not already completed or cancelled)
    if order.status in ['COMPLETED', 'CANCELLED']:
        messages.error(request, f'Order #{order.id} cannot be cancelled because it is already {order.get_status_display().lower()}')
        return redirect('view_order', order_id=order.id)

    if request.method == 'POST':
        cancellation_reason = request.POST.get('cancellation_reason', 'OTHER')
        cancellation_notes = request.POST.get('cancellation_notes', '')

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
                    reason=f"Order cancelled: {dict(Order.CANCELLATION_REASON_CHOICES).get(cancellation_reason, 'Other reason')}",
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
                messages.info(request, f'Table {order.table_number} has been released')

            # 4. Log activity
            StaffActivity.objects.create(
                staff=request.user,
                action='CANCEL_ORDER',
                details=f"Cancelled order #{order.id}. Reason: {dict(Order.CANCELLATION_REASON_CHOICES).get(cancellation_reason, 'Other reason')}",
                ip_address=get_client_ip(request)
            )

        messages.success(request, f'Order #{order.id} has been cancelled successfully')
        return redirect('cashier_orders_list')

    context = {
        'order': order,
        'cancellation_reasons': Order.CANCELLATION_REASON_CHOICES,
        'active_section': 'orders'
    }

    return render(request, 'cashier/cancel_order.html', context)


@login_required
def reservations_list(request):
    """View for cashiers to see and process confirmed reservations"""
    today = timezone.now().date()

    # Get confirmed reservations for today
    reservations = Reservation.objects.filter(
        status='CONFIRMED',
        date=today
    ).order_by('time')

    # Filter by processed status if requested
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'unprocessed':
        reservations = reservations.filter(is_processed=False)
    elif status_filter == 'processed':
        reservations = reservations.filter(is_processed=True)

    context = {
        'reservations': reservations,
        'status_filter': status_filter,
        'today': today,
        'active_section': 'reservations_list'
    }

    return render(request, 'cashier/reservations_list.html', context)


@login_required
def process_reservation(request, reservation_id):
    """Process a confirmed reservation and create an order"""
    reservation = get_object_or_404(Reservation, id=reservation_id, status='CONFIRMED')

    # Check if already processed
    if reservation.is_processed:
        messages.warning(request, f'Reservation #{reservation_id} has already been processed.')
        return redirect('reservations_list')

    if request.method == 'POST':
        with transaction.atomic():
            # Mark reservation as processed
            reservation.is_processed = True
            reservation.processed_by = request.user
            reservation.processed_at = timezone.now()
            reservation.save()

            # Create a new order for this reservation
            order = Order.objects.create(
                user=reservation.user,
                status='PENDING',
                order_type='DINE_IN',
                payment_method='CASH',  # Default, can be changed later
                payment_status='PENDING',
                table_number=reservation.table_number,
                number_of_guests=reservation.party_size,
                special_instructions=reservation.special_requests,
                created_by=request.user,
                total_amount=Decimal('0.00'),  # Default value, will be updated when items are added
                tax_amount=Decimal('0.00'),
                delivery_fee=Decimal('0.00'),
                discount_amount=Decimal('0.00')
            )

            # Log the activity
            StaffActivity.objects.create(
                staff=request.user,
                action='PROCESS_RESERVATION',
                details=f"Processed reservation #{reservation_id} and created order #{order.id}"
            )

            messages.success(request, f'Reservation #{reservation_id} has been processed. Order #{order.id} created.')
            return redirect('view_order', order_id=order.id)

    # Get menu items for the order creation form
    menu_items = MenuItem.objects.filter(is_available=True).order_by('category', 'name')
    categories = Category.objects.filter(is_active=True)

    context = {
        'reservation': reservation,
        'menu_items': menu_items,
        'categories': categories,
        'active_section': 'reservations_list'
    }

    return render(request, 'cashier/process_reservation.html', context)


@login_required
def pending_reservation_payments(request):
    """View for cashiers to see and verify pending reservation payments"""
    # Get pending reservation payments
    pending_payments = ReservationPayment.objects.filter(status='PENDING').order_by('-payment_date')

    context = {
        'pending_payments': pending_payments,
        'active_section': 'pending_reservation_payments'
    }

    return render(request, 'cashier/pending_reservation_payments.html', context)


@login_required
def view_reservation_payment(request, payment_id):
    """View details of a reservation payment"""
    payment = get_object_or_404(ReservationPayment, id=payment_id)

    context = {
        'payment': payment,
        'active_section': 'pending_reservation_payments'
    }

    return render(request, 'cashier/view_reservation_payment.html', context)


@login_required
def verify_reservation_payment(request, payment_id):
    """Verify a reservation payment"""
    payment = get_object_or_404(ReservationPayment, id=payment_id)

    if request.method == 'POST':
        # Mark payment as completed
        payment.status = 'COMPLETED'
        payment.verified_by = request.user
        payment.verification_date = timezone.now()
        payment.save()

        # Update reservation status
        reservation = payment.reservation
        reservation.status = 'CONFIRMED'
        reservation.save()

        # Log the activity
        StaffActivity.objects.create(
            staff=request.user,
            action='VERIFY_RESERVATION_PAYMENT',
            details=f"Verified payment of ₱{payment.amount} for Reservation #{reservation.id}"
        )

        messages.success(request, f'Payment for Reservation #{reservation.id} has been verified successfully!')
        return redirect('pending_reservation_payments')

    return redirect('view_reservation_payment', payment_id=payment_id)


@login_required
def reject_reservation_payment(request, payment_id):
    """Reject a reservation payment"""
    payment = get_object_or_404(ReservationPayment, id=payment_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Payment rejected')

        # Mark payment as failed
        payment.status = 'FAILED'
        payment.notes = reason
        payment.verified_by = request.user
        payment.verification_date = timezone.now()
        payment.save()

        # Log the activity
        StaffActivity.objects.create(
            staff=request.user,
            action='REJECT_RESERVATION_PAYMENT',
            details=f"Rejected payment for Reservation #{payment.reservation.id}. Reason: {reason}"
        )

        messages.success(request, f'Payment for Reservation #{payment.reservation.id} has been rejected.')
        return redirect('pending_reservation_payments')

    return redirect('view_reservation_payment', payment_id=payment_id)
