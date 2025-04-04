from .views import get_cart_count
from django.utils import timezone
from .models import Reservation, ReservationPayment

def cart_processor(request):
    """Add cart count to all templates"""
    return {
        'cart_count': get_cart_count(request)
    }

def reservation_processor(request):
    """Add reservation notifications to all templates"""
    # Only process for authenticated users with staff roles
    if not request.user.is_authenticated or not hasattr(request.user, 'staff_profile'):
        return {}

    # Get today's confirmed reservations for cashiers
    today = timezone.now().date()
    confirmed_reservations = Reservation.objects.filter(
        status='CONFIRMED',
        date=today
    ).order_by('time')

    # Count of unprocessed confirmed reservations for cashiers
    unprocessed_count = confirmed_reservations.filter(is_processed=False).count()

    # Count of pending reservation payments for cashiers
    pending_payments_count = ReservationPayment.objects.filter(status='PENDING').count()

    # Count of pending reservations for managers
    pending_reservations_count = Reservation.objects.filter(status='PENDING').count()

    # Get recent pending reservations for managers (last 24 hours)
    yesterday = timezone.now() - timezone.timedelta(days=1)
    recent_pending_reservations = Reservation.objects.filter(
        status='PENDING',
        created_at__gte=yesterday
    ).order_by('-created_at')[:5]

    return {
        'confirmed_reservations': confirmed_reservations,
        'unprocessed_reservations_count': unprocessed_count,
        'pending_reservation_payments_count': pending_payments_count,
        'pending_reservations_count': pending_reservations_count,
        'recent_pending_reservations': recent_pending_reservations
    }
