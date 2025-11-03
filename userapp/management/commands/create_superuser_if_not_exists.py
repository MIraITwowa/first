from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings


class Command(BaseCommand):
    help = 'Create superuser if it does not exist'

    def handle(self, *args, **options):
        User = get_user_model()
        
        if not getattr(settings, 'CREATE_SUPERUSER', False):
            self.stdout.write(
                self.style.WARNING('CREATE_SUPERUSER is not set. Skipping superuser creation.')
            )
            return
        
        username = getattr(settings, 'SUPERUSER_USERNAME', 'admin')
        email = getattr(settings, 'SUPERUSER_EMAIL', 'admin@example.com')
        password = getattr(settings, 'SUPERUSER_PASSWORD', 'admin123')
        
        if User.objects.filter(account=username).exists():
            self.stdout.write(
                self.style.SUCCESS(f'Superuser "{username}" already exists.')
            )
            return
        
        try:
            User.objects.create_superuser(
                account=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created superuser "{username}"')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create superuser: {e}')
            )