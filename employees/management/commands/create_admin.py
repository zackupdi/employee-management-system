import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update the configured admin user"

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "admin")
        password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")

        if not password:
            raise CommandError(
                "Set BOOTSTRAP_ADMIN_PASSWORD before running create_admin."
            )

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save(update_fields=["is_staff", "is_superuser", "is_active", "password"])

        state = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Admin user {state} successfully."))
