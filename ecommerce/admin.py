from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from .models import (
    Category, MenuItem, Reservation, Order, 
    OrderItem, Review, Cart, CartItem
)

class CustomAdminSite(admin.AdminSite):
    site_header = '5th Avenue Restaurant Administration'
    site_title = '5th Avenue Admin Portal'
    index_title = 'Restaurant Management Dashboard'

admin_site = CustomAdminSite()

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_count', 'is_active', 'display_image')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    def item_count(self, obj):
        return obj.menu_items.count()
    item_count.short_description = 'Number of Items'

    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.image.url)
        return "No image"
    display_image.short_description = 'Image'

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available', 'is_featured', 'display_image', 'average_rating')
    list_filter = ('category', 'is_available', 'is_featured', 'is_vegetarian', 'spice_level')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_available', 'is_featured', 'price')

    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 8px; object-fit: cover;" />', obj.image.url)
        return "No image"
    display_image.short_description = 'Image'

    def average_rating(self, obj):
        avg = obj.reviews.aggregate(Avg('rating'))['rating__avg']
        if avg:
            stars = '★' * int(round(avg))
            return format_html('<span style="color: #FFD700;">{}</span> ({:.1f})', stars, avg)
        return "No ratings"
    average_rating.short_description = 'Rating'

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'time', 'party_size', 'status', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Guest Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Reservation Details', {
            'fields': ('date', 'time', 'party_size', 'special_requests')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('System Fields', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_status_color(self, obj):
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'green',
            'CANCELLED': 'red'
        }
        return colors.get(obj.status, 'black')

    def status(self, obj):
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            self.get_status_color(obj),
            obj.get_status_display()
        )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('subtotal',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'menu_item', 'display_rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'menu_item__name', 'comment')
    readonly_fields = ('created_at', 'updated_at')

    def display_rating(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #FFD700;">{}</span>', stars)
    display_rating.short_description = 'Rating'

# Register remaining models
admin.site.register(Cart)
admin.site.register(CartItem)

# Custom admin dashboard
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

@staff_member_required
def admin_dashboard(request):
    # Get today's date
    today = timezone.now().date()
    
    # Calculate statistics
    context = {
        'total_orders': Order.objects.count(),
        'today_orders': Order.objects.filter(created_at__date=today).count(),
        'total_revenue': Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'today_revenue': Order.objects.filter(created_at__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'pending_reservations': Reservation.objects.filter(status='PENDING').count(),
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'popular_items': MenuItem.objects.annotate(order_count=Count('orderitem')).order_by('-order_count')[:5],
        'recent_reviews': Review.objects.select_related('user', 'menu_item').order_by('-created_at')[:5],
    }
    
# Register your models here.
