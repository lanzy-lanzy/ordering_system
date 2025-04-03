from django.contrib import admin
from django.urls import path
from .views import (
    home, filter_menu, menu, add_to_cart, view_cart, update_cart_item, checkout, gcash_payment, order_confirmation,
    user_login, user_logout, user_register, user_dashboard, add_menu_item, menu_items_list, categories_list,
    orders_list, reservations_list, reviews_list, user_settings,
    edit_menu_item, delete_menu_item, edit_category, delete_category,
    customer_dashboard, my_orders, my_reviews, profile, change_password,
    make_reservation, my_reservations, cancel_reservation, update_reservation_status
)
from .admin import admin_dashboard
from .inventory import (
    inventory_dashboard, add_inventory, inventory_history,
    sales_dashboard, price_history, item_sales_history
)
from .staff import (
    staff_list, add_staff, edit_staff, reset_staff_password,
    staff_activity, staff_profile_view
)
from .cashier import (
    cashier_dashboard, new_order, view_order, update_order_status, update_prep_time,
    orders_list as cashier_orders_list, print_receipt, print_multiple_receipts,
    pending_payments, view_payment, verify_payment, reject_payment, record_payment
)
from .manager import (
    manager_dashboard, sales_report, inventory_overview,
    staff_overview, performance_metrics, reservations_dashboard
)
from .customer_management import (
    customer_list, customer_detail, blacklist_customer, unblacklist_customer
)

urlpatterns = [
    path('', home, name='home'),
    path('menu/', menu, name='menu'),
    path('filter-menu/', filter_menu, name='filter_menu'),
    path('add-to-cart/<int:item_id>/', add_to_cart, name='add_to_cart'),
    path('cart/', view_cart, name='view_cart'),
    path('update-cart-item/<int:item_id>/', update_cart_item, name='update_cart_item'),
    path('checkout/', checkout, name='checkout'),
    path('gcash-payment/<int:order_id>/', gcash_payment, name='gcash_payment'),
    path('order-confirmation/<int:order_id>/', order_confirmation, name='order_confirmation'),
    # Admin URLs are defined in the root urls.py

    # Authentication URLs
    path('accounts/login/', user_login, name='login'),
    path('accounts/register/', user_register, name='register'),
    path('accounts/logout/', user_logout, name='logout'),

    # User Dashboard
    path('dashboard/', user_dashboard, name='dashboard'),
    path('customer/dashboard/', customer_dashboard, name='customer_dashboard'),
    path('customer/orders/', my_orders, name='my_orders'),
    path('customer/reviews/', my_reviews, name='my_reviews'),
    path('customer/profile/', profile, name='profile'),
    path('customer/change-password/', change_password, name='change_password'),

    # Menu Management
    path('dashboard/menu/', menu_items_list, name='menu_items'),
    path('dashboard/menu/add/', add_menu_item, name='add_menu_item'),
    path('dashboard/menu/edit/<int:item_id>/', edit_menu_item, name='edit_menu_item'),
    path('dashboard/menu/delete/<int:item_id>/', delete_menu_item, name='delete_menu_item'),

    # Categories Management
    path('dashboard/categories/', categories_list, name='categories'),
    path('dashboard/categories/edit/<int:category_id>/', edit_category, name='edit_category'),
    path('dashboard/categories/delete/<int:category_id>/', delete_category, name='delete_category'),

    # Orders Management
    path('dashboard/orders/', orders_list, name='orders'),

    # Reservations Management
    path('dashboard/reservations/', reservations_list, name='reservations'),
    path('dashboard/reservations/<int:reservation_id>/update-status/', update_reservation_status, name='update_reservation_status'),

    # Customer Reservations
    path('reservations/', make_reservation, name='make_reservation'),
    path('customer/reservations/', my_reservations, name='my_reservations'),
    path('customer/reservations/<int:reservation_id>/cancel/', cancel_reservation, name='cancel_reservation'),

    # Reviews Management
    path('dashboard/reviews/', reviews_list, name='reviews'),

    # User Settings
    path('dashboard/profile/', profile, name='user_profile'),
    path('dashboard/settings/', user_settings, name='user_settings'),

    # Inventory Management
    path('dashboard/inventory/', inventory_dashboard, name='inventory_dashboard'),
    path('dashboard/inventory/add/', add_inventory, name='add_inventory'),
    path('dashboard/inventory/history/', inventory_history, name='inventory_history'),
    path('dashboard/inventory/history/<int:item_id>/', inventory_history, name='item_inventory_history'),

    # Sales Analysis
    path('dashboard/sales/', sales_dashboard, name='sales_dashboard'),
    path('dashboard/sales/item/<int:item_id>/', item_sales_history, name='item_sales_history'),
    path('dashboard/price-history/', price_history, name='price_history'),
    path('dashboard/price-history/<int:item_id>/', price_history, name='item_price_history'),

    # Staff Management
    path('dashboard/staff/', staff_list, name='staff_list'),
    path('dashboard/staff/add/', add_staff, name='add_staff'),
    path('dashboard/staff/<int:user_id>/edit/', edit_staff, name='edit_staff'),
    path('dashboard/staff/<int:user_id>/reset-password/', reset_staff_password, name='reset_staff_password'),
    path('dashboard/staff/activity/', staff_activity, name='staff_activity'),
    path('dashboard/staff-profile/', staff_profile_view, name='staff_profile'),

    # Customer Management
    path('dashboard/customers/', customer_list, name='customer_list'),
    path('dashboard/customers/<int:user_id>/', customer_detail, name='customer_detail'),
    path('dashboard/customers/<int:user_id>/blacklist/', blacklist_customer, name='blacklist_customer'),
    path('dashboard/customers/<int:user_id>/unblacklist/', unblacklist_customer, name='unblacklist_customer'),

    # Cashier Dashboard
    path('cashier/', cashier_dashboard, name='cashier_dashboard'),
    path('cashier/new-order/', new_order, name='new_order'),
    path('cashier/orders/', cashier_orders_list, name='cashier_orders_list'),
    path('cashier/order/<int:order_id>/', view_order, name='view_order'),
    path('cashier/order/<int:order_id>/update-status/', update_order_status, name='update_order_status'),
    path('cashier/order/<int:order_id>/update-prep-time/', update_prep_time, name='update_prep_time'),
    path('cashier/order/<int:order_id>/receipt/', print_receipt, name='print_receipt'),
    path('cashier/print-multiple-receipts/', print_multiple_receipts, name='print_multiple_receipts'),
    path('cashier/order/<int:order_id>/payment/', record_payment, name='record_payment'),

    # Payment Management
    path('cashier/payments/', pending_payments, name='pending_payments'),
    path('cashier/payment/<int:payment_id>/', view_payment, name='view_payment'),
    path('cashier/payment/<int:payment_id>/verify/', verify_payment, name='verify_payment'),
    path('cashier/payment/<int:payment_id>/reject/', reject_payment, name='reject_payment'),

    # Manager Dashboard
    path('manager/', manager_dashboard, name='manager_dashboard'),
    path('manager/sales-report/', sales_report, name='sales_report'),
    path('manager/inventory-overview/', inventory_overview, name='inventory_overview'),
    path('manager/staff-overview/', staff_overview, name='staff_overview'),
    path('manager/performance-metrics/', performance_metrics, name='performance_metrics'),
    path('manager/reservations/', reservations_dashboard, name='reservations_dashboard'),
]
