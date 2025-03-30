from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ecommerce.models import StaffProfile

class Command(BaseCommand):
    help = 'Updates all superuser accounts to have the ADMIN role in their staff profiles'

    def handle(self, *args, **options):
        # Get all superusers
        superusers = User.objects.filter(is_superuser=True)
        
        if not superusers.exists():
            self.stdout.write(self.style.WARNING('No superusers found in the system.'))
            return
        
        updated_count = 0
        
        for user in superusers:
            try:
                # Check if user has a staff profile
                if hasattr(user, 'staff_profile'):
                    # Update role to ADMIN if it's not already
                    if user.staff_profile.role != 'ADMIN':
                        user.staff_profile.role = 'ADMIN'
                        user.staff_profile.save()
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Updated {user.username} role to ADMIN'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'{user.username} already has ADMIN role'))
                else:
                    # Create staff profile with ADMIN role
                    StaffProfile.objects.create(user=user, role='ADMIN')
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created ADMIN staff profile for {user.username}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating {user.username}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} superuser(s) to have ADMIN role'))
