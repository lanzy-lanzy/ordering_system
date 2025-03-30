from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import F, Sum, Avg, Count
from django.db.models.signals import post_save
from django.dispatch import receiver
import decimal

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, related_name='menu_items', null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='menu_items/')
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    spice_level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0
    )
    current_stock = models.PositiveIntegerField(default=0)
    stock_alert_threshold = models.PositiveIntegerField(default=10)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    @property
    def profit_margin(self):
        if self.cost_price > 0:
            return ((self.price - self.cost_price) / self.price) * 100
        return 0

    @property
    def stock_status(self):
        if self.current_stock <= 0:
            return 'Out of Stock'
        elif self.current_stock < self.stock_alert_threshold:
            return 'Low Stock'
        else:
            return 'In Stock'

    @property
    def total_sales_count(self):
        return OrderItem.objects.filter(menu_item=self).aggregate(Sum('quantity'))['quantity__sum'] or 0

    @property
    def total_sales_amount(self):
        return OrderItem.objects.filter(menu_item=self).aggregate(
            total=Sum(F('quantity') * F('price')))['total'] or 0

    def save(self, *args, **kwargs):
        # Check if this is an update and price has changed
        if self.pk:
            try:
                old_instance = MenuItem.objects.get(pk=self.pk)
                if old_instance.price != self.price:
                    # Create price history record
                    PriceHistory.objects.create(
                        menu_item=self,
                        old_price=old_instance.price,
                        new_price=self.price,
                        notes='Price updated'
                    )
            except MenuItem.DoesNotExist:
                pass

        super().save(*args, **kwargs)

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled')
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    date = models.DateField()
    time = models.TimeField()
    party_size = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Number of guests"
    )
    special_requests = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']

    def clean(self):
        if self.date < timezone.now().date():
            raise ValidationError("Reservation date cannot be in the past")
        if self.date == timezone.now().date() and self.time < timezone.now().time():
            raise ValidationError("Reservation time cannot be in the past")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reservation for {self.name} - {self.date} {self.time}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PREPARING', 'Preparing'),
        ('READY', 'Ready for Pickup'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]

    ORDER_TYPE_CHOICES = [
        ('DELIVERY', 'Delivery'),
        ('PICKUP', 'Pickup'),
        ('DINE_IN', 'Dine In'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash on Delivery'),
        ('CARD', 'Credit/Debit Card'),
        ('GCASH', 'GCash'),
        ('ONLINE', 'Other Online Payment'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    items = models.ManyToManyField(MenuItem, through='OrderItem')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, default='DELIVERY')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_address = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    special_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

    def calculate_total(self):
        return sum(item.subtotal for item in self.order_items.all())

    @property
    def grand_total(self):
        """Calculate the grand total including tax, delivery fee, and discounts"""
        return self.total_amount + self.tax_amount + self.delivery_fee - self.discount_amount

class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Order.PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_payments')
    verification_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of ${self.amount} for Order #{self.order.id} via {self.get_payment_method_display()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update order payment status if this payment is completed
        if self.status == 'COMPLETED' and self.order.payment_status != 'PAID':
            self.order.payment_status = 'PAID'
            self.order.save(update_fields=['payment_status'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    special_instructions = models.TextField(blank=True)
    inventory_updated = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'menu_item']

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} in Order #{self.order.id}"

    @property
    def subtotal(self):
        return self.quantity * self.price

    def save(self, *args, **kwargs):
        # Call the original save method
        super().save(*args, **kwargs)

        # Update inventory if not already updated
        if not self.inventory_updated and self.order.status != 'CANCELLED':
            # Create inventory transaction for this sale
            try:
                InventoryTransaction.objects.create(
                    menu_item=self.menu_item,
                    transaction_type='SALE',
                    quantity=-self.quantity,  # Negative because it's reducing stock
                    unit_price=self.price,
                    total_price=self.subtotal,
                    reference=f"Order #{self.order.id}",
                    notes=f"Sale through order #{self.order.id}"
                )
            except Exception as e:
                # Log the error but don't stop the process
                print(f"Error creating inventory transaction: {str(e)}")

            # Update sales summary for the day
            today = timezone.now().date()
            summary, created = SalesSummary.objects.get_or_create(
                menu_item=self.menu_item,
                date=today,
                defaults={
                    'quantity_sold': 0,
                    'revenue': 0,
                    'cost': 0,
                    'profit': 0
                }
            )

            # Update the summary
            try:
                cost_per_item = self.menu_item.cost_price
                item_cost = cost_per_item * self.quantity
                item_profit = self.subtotal - item_cost

                summary.quantity_sold += self.quantity
                summary.revenue += self.subtotal
                summary.cost += item_cost
                summary.profit += item_profit
            except (TypeError, decimal.InvalidOperation):
                # Handle case where cost_price might be None or invalid
                summary.quantity_sold += self.quantity
                summary.revenue += self.subtotal
                # Use default values for cost and profit if calculation fails
                summary.cost += 0
                summary.profit += self.subtotal  # Assume 100% profit if cost is invalid

            summary.save()

            # Mark as updated
            self.inventory_updated = True
            super().save(update_fields=['inventory_updated'])

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'menu_item']

    def __str__(self):
        return f"Review by {self.user.username} for {self.menu_item.name}"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    items = models.ManyToManyField(MenuItem, through='CartItem')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.cart_items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_instructions = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'menu_item']

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} in {self.cart.user.username}'s cart"

    @property
    def subtotal(self):
        return self.quantity * self.menu_item.price


class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Purchase'),
        ('SALE', 'Sale'),
        ('ADJUSTMENT', 'Adjustment'),
        ('RETURN', 'Return'),
        ('WASTE', 'Waste/Loss'),
        ('INITIAL', 'Initial Stock')
    ]

    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='inventory_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField(help_text='Positive for additions, negative for reductions')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference = models.CharField(max_length=100, blank=True, help_text='Order number, invoice number, etc.')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    previous_stock = models.PositiveIntegerField(default=0)
    new_stock = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.menu_item.name} ({self.quantity}) on {self.created_at.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        # Calculate total price if unit price is provided
        if self.unit_price and not self.total_price:
            try:
                self.total_price = self.unit_price * abs(self.quantity)
            except (TypeError, decimal.InvalidOperation):
                # Handle case where unit_price might be None or invalid
                self.total_price = 0

        # Record previous stock
        self.previous_stock = self.menu_item.current_stock

        # Update menu item stock
        self.menu_item.current_stock += self.quantity
        if self.menu_item.current_stock < 0:
            self.menu_item.current_stock = 0
        self.menu_item.save()

        # Record new stock
        self.new_stock = self.menu_item.current_stock

        super().save(*args, **kwargs)


class PriceHistory(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='price_history')
    old_price = models.DecimalField(max_digits=10, decimal_places=2)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = 'Price histories'

    def __str__(self):
        return f"{self.menu_item.name} - ${self.old_price} to ${self.new_price} on {self.changed_at.strftime('%Y-%m-%d')}"


class SalesSummary(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='sales_summaries')
    date = models.DateField()
    quantity_sold = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Sales summaries'
        unique_together = ['menu_item', 'date']

    def __str__(self):
        return f"{self.menu_item.name} - {self.date} - {self.quantity_sold} sold"


# Staff Management Models
class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('CASHIER', 'Cashier'),
        ('KITCHEN', 'Kitchen Staff'),
        ('WAITER', 'Waiter/Waitress'),
        ('DELIVERY', 'Delivery Person'),
        ('CUSTOMER', 'Customer'),  # Added for regular customers
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CASHIER')
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    hire_date = models.DateField(default=timezone.now)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    is_active_staff = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_staff')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'
        permissions = [
            ('manage_staff', 'Can manage staff members'),
            ('view_sales_reports', 'Can view sales reports'),
            ('manage_inventory', 'Can manage inventory'),
            ('process_orders', 'Can process orders'),
            ('manage_menu', 'Can manage menu items'),
            ('manage_customers', 'Can manage customers'),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()}"

    def save(self, *args, **kwargs):
        # Generate employee ID if not provided
        if not self.employee_id:
            # Format: EMP-YEAR-XXXX (e.g., EMP-2023-0001)
            year = timezone.now().year
            last_emp = StaffProfile.objects.filter(employee_id__contains=f'EMP-{year}').order_by('employee_id').last()

            if last_emp:
                # Extract the last number and increment
                try:
                    last_num = int(last_emp.employee_id.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            self.employee_id = f'EMP-{year}-{new_num:04d}'

        # Set appropriate permissions based on role
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating:
            self.set_role_permissions()

    def set_role_permissions(self):
        """Set appropriate permissions based on staff role"""
        user = self.user

        # Clear existing groups
        user.groups.clear()

        # Get or create the appropriate group
        group_name = f"{self.get_role_display()} Group"
        group, created = Group.objects.get_or_create(name=group_name)

        # Set permissions based on role
        if created:
            if self.role == 'ADMIN':
                # Admins get all permissions
                permissions = Permission.objects.all()
                group.permissions.set(permissions)
            elif self.role == 'MANAGER':
                # Managers get most permissions except user management
                content_types = ContentType.objects.filter(app_label='ecommerce')
                permissions = Permission.objects.filter(content_type__in=content_types)
                group.permissions.set(permissions)
                # Add specific permissions
                group.permissions.add(Permission.objects.get(codename='manage_staff'))
                group.permissions.add(Permission.objects.get(codename='view_sales_reports'))
                group.permissions.add(Permission.objects.get(codename='manage_inventory'))
                group.permissions.add(Permission.objects.get(codename='manage_menu'))
                group.permissions.add(Permission.objects.get(codename='manage_customers'))
            elif self.role == 'CASHIER':
                # Cashiers can process orders and view products
                try:
                    # Add process_orders permission
                    process_orders_perm = Permission.objects.get(codename='process_orders')
                    group.permissions.add(process_orders_perm)
                    # Add it directly to the user as well for redundancy
                    self.user.user_permissions.add(process_orders_perm)
                except Permission.DoesNotExist:
                    print(f"Warning: process_orders permission not found for user {self.user.username}")

                # Add view permissions
                try:
                    group.permissions.add(Permission.objects.get(codename='view_menuitem'))
                except Permission.DoesNotExist:
                    print(f"Warning: view_menuitem permission not found")

                try:
                    group.permissions.add(Permission.objects.get(codename='view_order'))
                except Permission.DoesNotExist:
                    print(f"Warning: view_order permission not found")

                # Add change_order permission
                try:
                    group.permissions.add(Permission.objects.get(codename='change_order'))
                except Permission.DoesNotExist:
                    print(f"Warning: change_order permission not found")
            elif self.role == 'KITCHEN':
                # Kitchen staff can view orders and update order status
                group.permissions.add(Permission.objects.get(codename='view_order'))
                group.permissions.add(Permission.objects.get(codename='change_order'))
            elif self.role == 'WAITER':
                # Waiters can create and view orders
                group.permissions.add(Permission.objects.get(codename='add_order'))
                group.permissions.add(Permission.objects.get(codename='view_order'))
                group.permissions.add(Permission.objects.get(codename='view_menuitem'))
            elif self.role == 'DELIVERY':
                # Delivery staff can view and update orders
                group.permissions.add(Permission.objects.get(codename='view_order'))
                group.permissions.add(Permission.objects.get(codename='change_order'))

        # Add user to the group
        user.groups.add(group)

        # Set staff status based on role
        if self.role in ['ADMIN', 'MANAGER']:
            user.is_staff = True
        else:
            user.is_staff = False

        # Save the user
        user.save()


class StaffActivity(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('CREATE_ORDER', 'Created Order'),
        ('UPDATE_ORDER', 'Updated Order'),
        ('CANCEL_ORDER', 'Cancelled Order'),
        ('ADD_ITEM', 'Added Menu Item'),
        ('UPDATE_ITEM', 'Updated Menu Item'),
        ('DELETE_ITEM', 'Deleted Menu Item'),
        ('ADD_INVENTORY', 'Added Inventory'),
        ('BLACKLIST_CUSTOMER', 'Blacklisted Customer'),
        ('UNBLACKLIST_CUSTOMER', 'Removed Customer from Blacklist'),
        ('OTHER', 'Other Activity'),
    ]

    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Staff Activity'
        verbose_name_plural = 'Staff Activities'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


# Customer Profile Model
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    profile_picture = models.ImageField(upload_to='customer_profiles/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    favorite_food = models.CharField(max_length=100, blank=True)
    dietary_preferences = models.TextField(blank=True, help_text="Vegetarian, Vegan, Gluten-Free, etc.")
    allergies = models.TextField(blank=True)
    is_blacklisted = models.BooleanField(default=False, help_text="Whether this customer is blacklisted")
    blacklist_reason = models.TextField(blank=True, help_text="Reason for blacklisting this customer")
    blacklisted_at = models.DateTimeField(null=True, blank=True, help_text="When this customer was blacklisted")
    blacklisted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='blacklisted_customers', help_text="Staff member who blacklisted this customer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer Profile'
        verbose_name_plural = 'Customer Profiles'

    def __str__(self):
        return f"Profile for {self.user.username}"

    @property
    def full_address(self):
        """Return the full address as a formatted string"""
        parts = [self.address]
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.zip_code:
            parts.append(self.zip_code)
        return ", ".join(filter(None, parts))

    @property
    def total_orders(self):
        """Return the total number of orders placed by this customer"""
        return Order.objects.filter(user=self.user).count()

    @property
    def total_spent(self):
        """Return the total amount spent by this customer"""
        return Order.objects.filter(user=self.user).aggregate(models.Sum('total_amount'))['total_amount__sum'] or 0


# Signal to create profiles when a user is created
@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    """Create profiles when a new user is created"""
    if created:
        # Create the appropriate profile based on user type
        if instance.is_staff or instance.is_superuser:
            # Create staff profile for staff users
            StaffProfile.objects.create(user=instance)
        else:
            # Create customer profile for regular users
            CustomerProfile.objects.create(user=instance)
            # Also create a minimal staff profile for internal use
            # This is needed because some code may expect it to exist
            StaffProfile.objects.create(
                user=instance,
                role='CUSTOMER',  # Using CASHIER as it's the default, but this user isn't actually staff
                is_active_staff=False
            )


# Signal to save profiles when a user is saved
@receiver(post_save, sender=User)
def save_user_profiles(sender, instance, **kwargs):
    """Save the profiles when a user is saved"""
    if hasattr(instance, 'staff_profile'):
        instance.staff_profile.save()

    if hasattr(instance, 'customer_profile'):
        instance.customer_profile.save()
