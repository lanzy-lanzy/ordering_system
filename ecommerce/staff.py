from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import StaffProfile, StaffActivity
import datetime

@login_required
@permission_required('ecommerce.manage_staff', raise_exception=True)
def staff_list(request):
    """Display list of staff members"""
    # Get search query
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')

    # Base queryset
    staff_users = User.objects.filter(staff_profile__isnull=False).select_related('staff_profile')

    # Apply filters
    if query:
        staff_users = staff_users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(staff_profile__employee_id__icontains=query)
        )

    if role_filter:
        staff_users = staff_users.filter(staff_profile__role=role_filter)

    # Order by
    staff_users = staff_users.order_by('-date_joined')

    # Pagination
    paginator = Paginator(staff_users, 10)
    page_number = request.GET.get('page', 1)
    staff_page = paginator.get_page(page_number)

    context = {
        'staff_page': staff_page,
        'query': query,
        'role_filter': role_filter,
        'roles': StaffProfile.ROLE_CHOICES,
        'active_section': 'staff'
    }

    return render(request, 'accounts/staff_list.html', context)

@login_required
@permission_required('ecommerce.manage_staff', raise_exception=True)
def add_staff(request):
    """Add a new staff member"""
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        role = request.POST.get('role')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        hire_date = request.POST.get('hire_date', timezone.now().date())
        emergency_contact = request.POST.get('emergency_contact', '')
        emergency_phone = request.POST.get('emergency_phone', '')
        notes = request.POST.get('notes', '')

        # Validate required fields
        if not all([username, email, first_name, last_name, password, role]):
            messages.error(request, 'Please fill in all required fields')
            return redirect('add_staff')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" is already taken')
            return redirect('add_staff')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, f'Email "{email}" is already registered')
            return redirect('add_staff')

        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Update staff profile
            profile = user.staff_profile
            profile.role = role
            profile.phone = phone
            profile.address = address
            profile.hire_date = hire_date
            profile.emergency_contact = emergency_contact
            profile.emergency_phone = emergency_phone
            profile.notes = notes
            profile.created_by = request.user
            profile.save()

            # Log activity
            StaffActivity.objects.create(
                staff=request.user,
                action='OTHER',
                details=f'Added new staff member: {user.get_full_name()} ({profile.get_role_display()})',
                ip_address=get_client_ip(request)
            )

            messages.success(request, f'Staff member {user.get_full_name()} added successfully')
            return redirect('staff_list')

        except Exception as e:
            messages.error(request, f'Error adding staff member: {str(e)}')

    context = {
        'roles': StaffProfile.ROLE_CHOICES,
        'active_section': 'staff'
    }

    return render(request, 'accounts/add_staff.html', context)

@login_required
@permission_required('ecommerce.manage_staff', raise_exception=True)
def edit_staff(request, user_id):
    """Edit an existing staff member"""
    staff_user = get_object_or_404(User, id=user_id)
    staff_profile = staff_user.staff_profile

    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        hire_date = request.POST.get('hire_date')
        emergency_contact = request.POST.get('emergency_contact', '')
        emergency_phone = request.POST.get('emergency_phone', '')
        notes = request.POST.get('notes', '')
        is_active = request.POST.get('is_active') == 'on'

        # Check if email already exists for other users
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            messages.error(request, f'Email "{email}" is already registered to another user')
            return redirect('edit_staff', user_id=user_id)

        try:
            # Update user
            staff_user.email = email
            staff_user.first_name = first_name
            staff_user.last_name = last_name
            staff_user.is_active = is_active
            staff_user.save()

            # Update staff profile
            staff_profile.role = role
            staff_profile.phone = phone
            staff_profile.address = address
            staff_profile.hire_date = hire_date
            staff_profile.emergency_contact = emergency_contact
            staff_profile.emergency_phone = emergency_phone
            staff_profile.notes = notes
            staff_profile.is_active_staff = is_active
            staff_profile.save()

            # Log activity
            StaffActivity.objects.create(
                staff=request.user,
                action='OTHER',
                details=f'Updated staff member: {staff_user.get_full_name()} ({staff_profile.get_role_display()})',
                ip_address=get_client_ip(request)
            )

            messages.success(request, f'Staff member {staff_user.get_full_name()} updated successfully')
            return redirect('staff_list')

        except Exception as e:
            messages.error(request, f'Error updating staff member: {str(e)}')

    context = {
        'staff_user': staff_user,
        'staff_profile': staff_profile,
        'roles': StaffProfile.ROLE_CHOICES,
        'active_section': 'staff'
    }

    return render(request, 'accounts/edit_staff.html', context)

@login_required
@permission_required('ecommerce.manage_staff', raise_exception=True)
def reset_staff_password(request, user_id):
    """Reset password for a staff member"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

    staff_user = get_object_or_404(User, id=user_id)
    new_password = request.POST.get('new_password')

    if not new_password:
        return JsonResponse({'status': 'error', 'message': 'Password cannot be empty'})

    try:
        staff_user.set_password(new_password)
        staff_user.save()

        # Log activity
        StaffActivity.objects.create(
            staff=request.user,
            action='OTHER',
            details=f'Reset password for staff member: {staff_user.get_full_name()}',
            ip_address=get_client_ip(request)
        )

        return JsonResponse({'status': 'success', 'message': 'Password reset successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error resetting password: {str(e)}'})

@login_required
@permission_required('ecommerce.manage_staff', raise_exception=True)
def staff_activity(request):
    """View staff activity logs"""
    # Get filters
    staff_id = request.GET.get('staff_id')
    action_filter = request.GET.get('action')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Base queryset
    activities = StaffActivity.objects.all().select_related('staff')

    # Apply filters
    if staff_id:
        activities = activities.filter(staff_id=staff_id)

    if action_filter:
        activities = activities.filter(action=action_filter)

    if date_from:
        activities = activities.filter(timestamp__date__gte=date_from)

    if date_to:
        activities = activities.filter(timestamp__date__lte=date_to)

    # Order by most recent
    activities = activities.order_by('-timestamp')

    # Pagination
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page', 1)
    activity_page = paginator.get_page(page_number)

    # Get all staff for filter dropdown
    staff_users = User.objects.filter(staff_profile__isnull=False).order_by('first_name', 'last_name')

    context = {
        'activity_page': activity_page,
        'staff_users': staff_users,
        'staff_id': staff_id,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        'actions': StaffActivity.ACTION_CHOICES,
        'active_section': 'staff_activity'
    }

    return render(request, 'accounts/staff_activity.html', context)

@login_required
def staff_profile_view(request):
    """View and edit current staff profile"""
    staff_profile = request.user.staff_profile

    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        emergency_contact = request.POST.get('emergency_contact', '')
        emergency_phone = request.POST.get('emergency_phone', '')
        profile_picture = request.FILES.get('profile_picture')

        # Check if email already exists for other users
        if User.objects.filter(email=email).exclude(id=request.user.id).exists():
            messages.error(request, f'Email "{email}" is already registered to another user')
            return redirect('staff_profile')

        try:
            # Update user
            request.user.email = email
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save()

            # Update staff profile
            staff_profile.phone = phone
            staff_profile.address = address
            staff_profile.emergency_contact = emergency_contact
            staff_profile.emergency_phone = emergency_phone

            # Handle profile picture upload
            if profile_picture:
                staff_profile.profile_picture = profile_picture

            staff_profile.save()

            # Log activity
            StaffActivity.objects.create(
                staff=request.user,
                action='OTHER',
                details=f'Updated own profile information',
                ip_address=get_client_ip(request)
            )

            messages.success(request, 'Profile updated successfully')
            return redirect('staff_profile')

        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')

    # Get recent activities
    recent_activities = StaffActivity.objects.filter(staff=request.user).order_by('-timestamp')[:10]

    context = {
        'staff_profile': staff_profile,
        'recent_activities': recent_activities,
        'active_section': 'profile'
    }

    return render(request, 'accounts/staff_profile.html', context)

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
