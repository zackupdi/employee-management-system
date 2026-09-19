import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the default admin user"

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "admin")
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")

        if not password:
            self.stdout.write(
                self.style.ERROR("BOOTSTRAP_ADMIN_PASSWORD is not set.")
            )
            return

        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Admin user '{username}' {action} successfully."
            )
        )
