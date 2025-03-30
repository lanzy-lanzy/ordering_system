from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from ecommerce.models import StaffProfile

class Command(BaseCommand):
    help = 'Update permissions for cashier users'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to update cashier permissions...'))
        
        # Get all users with cashier role
        cashiers = StaffProfile.objects.filter(role='CASHIER')
        self.stdout.write(self.style.SUCCESS(f'Found {cashiers.count()} cashiers'))
        
        # Get or create the Cashier Group
        cashier_group, created = Group.objects.get_or_create(name='Cashier Group')
        
        # Get the process_orders permission
        try:
            process_orders_perm = Permission.objects.get(codename='process_orders')
            self.stdout.write(self.style.SUCCESS(f'Found process_orders permission'))
        except Permission.DoesNotExist:
            # If the permission doesn't exist, create it
            content_type = ContentType.objects.get_for_model(StaffProfile)
            process_orders_perm = Permission.objects.create(
                codename='process_orders',
                name='Can process orders',
                content_type=content_type,
            )
            self.stdout.write(self.style.SUCCESS(f'Created process_orders permission'))
        
        # Add the permission to the cashier group
        cashier_group.permissions.add(process_orders_perm)
        
        # Add view_order permission
        try:
            view_order_perm = Permission.objects.get(codename='view_order')
            cashier_group.permissions.add(view_order_perm)
            self.stdout.write(self.style.SUCCESS(f'Added view_order permission to cashier group'))
        except Permission.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'view_order permission not found'))
        
        # Add view_menuitem permission
        try:
            view_menuitem_perm = Permission.objects.get(codename='view_menuitem')
            cashier_group.permissions.add(view_menuitem_perm)
            self.stdout.write(self.style.SUCCESS(f'Added view_menuitem permission to cashier group'))
        except Permission.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'view_menuitem permission not found'))
        
        updated_count = 0
        
        for staff_profile in cashiers:
            try:
                user = staff_profile.user
                
                # Add user to the cashier group
                user.groups.add(cashier_group)
                
                # Add the permission directly to the user as well
                user.user_permissions.add(process_orders_perm)
                
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'Updated permissions for {user.username}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating {staff_profile.user.username}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated permissions for {updated_count} cashiers'))
