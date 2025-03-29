from django.urls import path
from .views import (
    home, filter_menu, menu, add_to_cart, user_login, user_logout,
    user_dashboard, add_menu_item, menu_items_list, categories_list,
    orders_list, reservations_list, reviews_list, user_settings,
    edit_menu_item, delete_menu_item, edit_category, delete_category,
    customer_dashboard, my_orders, my_reviews, profile, change_password
)
from .admin import admin_dashboard

urlpatterns = [
    path('', home, name='home'),
    path('menu/', menu, name='menu'),
    path('filter-menu/', filter_menu, name='filter_menu'),
    path('add-to-cart/<int:item_id>/', add_to_cart, name='add_to_cart'),
    path('restaurant-admin/dashboard/', admin_dashboard, name='admin_dashboard'),

    # Authentication URLs
    path('accounts/login/', user_login, name='login'),
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

    # Reviews Management
    path('dashboard/reviews/', reviews_list, name='reviews'),

    # User Settings
    path('dashboard/profile/', profile, name='user_profile'),
    path('dashboard/settings/', user_settings, name='user_settings'),
]
