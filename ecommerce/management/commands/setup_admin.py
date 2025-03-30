from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Sets up the admin user with correct permissions'

    def handle(self, *args, **options):
        try:
            # Create or update admin user
            admin_user, created = User.objects.get_or_create(username='admin')
            admin_user.set_password('admin123')
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.email = 'admin@example.com'
            admin_user.save()

            if created:
                self.stdout.write(self.style.SUCCESS('Admin user created successfully'))
            else:
                self.stdout.write(self.style.SUCCESS('Admin user updated successfully'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))