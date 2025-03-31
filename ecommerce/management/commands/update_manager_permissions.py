from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from ecommerce.models import StaffProfile

class Command(BaseCommand):
    help = 'Updates permissions for manager users'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting manager permissions update...'))
        
        # Get all users with manager role
        managers = User.objects.filter(staff_profile__role='MANAGER')
        self.stdout.write(f'Found {managers.count()} managers')
        
        # Get or create the Manager Group
        group_name = "Manager Group"
        group, created = Group.objects.get_or_create(name=group_name)
        
        if created or True:  # Always update permissions
            self.stdout.write('Updating manager group permissions...')
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add all ecommerce app permissions
            content_types = ContentType.objects.filter(app_label='ecommerce')
            permissions = Permission.objects.filter(content_type__in=content_types)
            group.permissions.set(permissions)
            
            # Add specific permissions
            specific_permissions = [
                'manage_staff',
                'view_sales_reports',
                'manage_inventory',
                'manage_menu',
                'process_orders',
                'manage_customers',
                'change_reservation',
                'view_reservation',
                'add_reservation',
                'delete_reservation'
            ]
            
            for perm_name in specific_permissions:
                try:
                    perm = Permission.objects.get(codename=perm_name)
                    group.permissions.add(perm)
                    self.stdout.write(f'Added permission: {perm_name}')
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Permission not found: {perm_name}'))
        
        # Update all managers
        updated_count = 0
        for user in managers:
            try:
                # Ensure user is in the manager group
                if group not in user.groups.all():
                    user.groups.add(group)
                    updated_count += 1
                
                # Ensure user has staff status
                if not user.is_staff:
                    user.is_staff = True
                    user.save()
                    updated_count += 1
                
                self.stdout.write(self.style.SUCCESS(f'Updated permissions for {user.username}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating {user.username}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} managers'))
