from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    Category, MenuItem, Reservation, Order,
    OrderItem, Review, Cart, CartItem,
    InventoryTransaction, PriceHistory, SalesSummary,
    StaffProfile, StaffActivity
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
    list_display = ('name', 'category', 'price', 'cost_price', 'profit_margin_display', 'current_stock', 'stock_status_display', 'is_available', 'display_image', 'total_sales')
    list_filter = ('category', 'is_available', 'is_featured', 'is_vegetarian', 'spice_level')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'profit_margin_display', 'stock_status_display', 'total_sales', 'total_revenue')
    list_editable = ('is_available', 'price', 'cost_price', 'current_stock')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'image')
        }),
        ('Pricing', {
            'fields': ('price', 'cost_price', 'profit_margin_display')
        }),
        ('Inventory', {
            'fields': ('current_stock', 'stock_alert_threshold', 'stock_status_display')
        }),
        ('Sales', {
            'fields': ('total_sales', 'total_revenue')
        }),
        ('Attributes', {
            'fields': ('is_available', 'is_featured', 'is_vegetarian', 'spice_level')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

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

    def profit_margin_display(self, obj):
        margin = obj.profit_margin
        if margin > 30:
            color = 'green'
        elif margin > 15:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{:.2f}%</span>', color, margin)
    profit_margin_display.short_description = 'Profit Margin'

    def stock_status_display(self, obj):
        status = obj.stock_status
        if status == 'In Stock':
            color = 'green'
        elif status == 'Low Stock':
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, status)
    stock_status_display.short_description = 'Stock Status'

    def total_sales(self, obj):
        return obj.total_sales_count
    total_sales.short_description = 'Units Sold'

    def total_revenue(self, obj):
        return format_html('${:.2f}', obj.total_sales_amount)
    total_revenue.short_description = 'Total Revenue'

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

# Register inventory and sales models
@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'transaction_type', 'quantity', 'unit_price', 'total_price', 'previous_stock', 'new_stock', 'created_at')
    list_filter = ('transaction_type', 'created_at', 'menu_item__category')
    search_fields = ('menu_item__name', 'reference', 'notes')
    readonly_fields = ('previous_stock', 'new_stock', 'created_at')
    date_hierarchy = 'created_at'

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'old_price', 'new_price', 'changed_at')
    list_filter = ('changed_at', 'menu_item__category')
    search_fields = ('menu_item__name', 'notes')
    readonly_fields = ('changed_at',)
    date_hierarchy = 'changed_at'

@admin.register(SalesSummary)
class SalesSummaryAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'date', 'quantity_sold', 'revenue', 'cost', 'profit', 'profit_margin')
    list_filter = ('date', 'menu_item__category')
    search_fields = ('menu_item__name',)
    date_hierarchy = 'date'

    def profit_margin(self, obj):
        if obj.revenue > 0:
            margin = (obj.profit / obj.revenue) * 100
            return f"{margin:.2f}%"
        return "0.00%"
    profit_margin.short_description = 'Profit Margin'

# Staff Profile Inline for User Admin
class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    can_delete = False
    verbose_name_plural = 'Staff Profile'
    fk_name = 'user'
    fields = ('role', 'employee_id', 'phone', 'address', 'hire_date', 'emergency_contact',
              'emergency_phone', 'is_active_staff', 'notes')

# Extend the User Admin
class CustomUserAdmin(UserAdmin):
    inlines = (StaffProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'get_employee_id', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'groups', 'staff_profile__role')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'staff_profile__employee_id')
    ordering = ('-date_joined',)

    def get_role(self, obj):
        if hasattr(obj, 'staff_profile'):
            return obj.staff_profile.get_role_display()
        return '-'
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'staff_profile__role'

    def get_employee_id(self, obj):
        if hasattr(obj, 'staff_profile'):
            return obj.staff_profile.employee_id
        return '-'
    get_employee_id.short_description = 'Employee ID'
    get_employee_id.admin_order_field = 'staff_profile__employee_id'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

@admin.register(StaffActivity)
class StaffActivityAdmin(admin.ModelAdmin):
    list_display = ('staff', 'action', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp', 'staff')
    search_fields = ('staff__username', 'staff__first_name', 'staff__last_name', 'details')
    readonly_fields = ('staff', 'action', 'details', 'ip_address', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

# Register remaining models
admin.site.register(Cart)
admin.site.register(CartItem)

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Custom admin dashboard
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Count, Sum
from django.utils import timezone
from .models import Order, MenuItem, Reservation, Review

@login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    # Check if user is superuser or has admin role
    if not request.user.is_superuser and not (hasattr(request.user, 'staff_profile') and request.user.staff_profile.role == 'ADMIN'):
        return redirect('login')

    # Get today's date
    today = timezone.now().date()

    # Calculate dashboard statistics
    context = {
        'today_orders': Order.objects.filter(created_at__date=today).count(),
        'total_orders': Order.objects.count(),
        'today_revenue': Order.objects.filter(created_at__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'total_revenue': Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'pending_reservations': Reservation.objects.filter(status='PENDING').count(),
        'today_reservations': Reservation.objects.filter(date=today).count(),
        'popular_items': MenuItem.objects.annotate(order_count=Count('orderitem')).order_by('-order_count')[:5],
        'recent_reviews': Review.objects.select_related('user', 'menu_item').order_by('-created_at')[:5],
    }

    # Get recent orders for the dashboard
    recent_orders = Order.objects.order_by('-created_at')[:5]
    context['recent_orders'] = recent_orders

    # Get pending reservations list
    pending_reservations_list = Reservation.objects.filter(status='PENDING').order_by('date', 'time')[:5]
    context['pending_reservations_list'] = pending_reservations_list

    # Add active section for sidebar highlighting
    context['active_section'] = 'dashboard'

    return render(request, 'admin/dashboard_new.html', context)

# Register your models here.
