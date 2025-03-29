from django.urls import path
from .views import home, filter_menu, menu, add_to_cart
from .admin import admin_dashboard

urlpatterns = [
    path('', home, name='home'),
    path('menu/', menu, name='menu'),
    path('filter-menu/', filter_menu, name='filter_menu'),
    path('add-to-cart/<int:item_id>/', add_to_cart, name='add_to_cart'),
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
]
