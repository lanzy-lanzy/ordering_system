from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip middleware for non-authenticated users or for login/logout/register views
        if not request.user.is_authenticated:
            return None

        # Skip for static files, admin, and media
        if request.path.startswith('/static/') or request.path.startswith('/media/') or request.path.startswith('/admin/'):
            return None

        # Get the current path
        current_path = request.path.strip('/')

        # Define role-specific paths
        cashier_paths = ['cashier', 'cashier/', 'cashier/dashboard', 'cashier/orders', 'cashier/new-order', 'cashier/payments', 'cashier/payment']
        manager_paths = ['manager', 'manager/']
        admin_paths = ['admin', 'admin/']
        customer_paths = ['customer', 'customer/dashboard', 'customer/orders', 'my-orders']

        # Common paths that all roles can access
        common_paths = ['', 'menu', 'cart', 'profile', 'change-password', 'logout', 'accounts/logout', 'accounts/logout/']

        print(f"Current path: {current_path}")

        # Check if user has a staff profile
        if hasattr(request.user, 'staff_profile'):
            user_role = request.user.staff_profile.role
            print(f"User role: {user_role}")

            # Cashier role restrictions
            if user_role == 'CASHIER':
                # Allow access to cashier paths
                if current_path.startswith('cashier/') or current_path == 'cashier':
                    print(f"Cashier accessing cashier path: {current_path}")
                    return None

                # Restrict access to manager and admin paths
                if (current_path.startswith('manager/') or
                    current_path.startswith('admin/') or
                    current_path in manager_paths or
                    current_path in admin_paths):
                    print(f"Cashier attempting to access restricted path: {current_path}")
                    messages.error(request, "You don't have permission to access that page.")
                    return redirect('cashier_dashboard')

                # If not a cashier path and not a common path, redirect to cashier dashboard
                if current_path not in common_paths and not current_path.startswith('cashier/'):
                    print(f"Cashier redirected from {current_path} to cashier dashboard")
                    return redirect('cashier_dashboard')

            # Manager role restrictions
            elif user_role == 'MANAGER':
                if (current_path.startswith('admin/') or
                    current_path in admin_paths):
                    messages.error(request, "You don't have permission to access that page.")
                    return redirect('manager_dashboard')

            # Customer role restrictions
            elif user_role == 'CUSTOMER':
                if (current_path.startswith('cashier/') or
                    current_path.startswith('manager/') or
                    current_path.startswith('admin/') or
                    current_path in cashier_paths or
                    current_path in manager_paths or
                    current_path in admin_paths):
                    messages.error(request, "You don't have permission to access that page.")
                    return redirect('customer_dashboard')

        # Default behavior for users without specific roles
        elif not request.user.is_staff and not request.user.is_superuser:
            if (current_path.startswith('cashier/') or
                current_path.startswith('manager/') or
                current_path.startswith('admin/') or
                current_path in cashier_paths or
                current_path in manager_paths or
                current_path in admin_paths):
                messages.error(request, "You don't have permission to access that page.")
                return redirect('customer_dashboard')

        return None
