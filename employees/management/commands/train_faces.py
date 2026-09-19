from django.core.management.base import BaseCommand, CommandError

from ... import face_service
from ...models import Employee


class Command(BaseCommand):
    help = 'Train the LBPH face model from employee photos.'

    def handle(self, *args, **options):
        employees = Employee.objects.filter(photo__isnull=False).exclude(photo='')
        if not employees.exists():
            self.stdout.write(self.style.WARNING('No employees with photos found.'))
            return
        try:
            trained = face_service.train_lbph()
        except RuntimeError as error:
            raise CommandError(str(error)) from error
        if trained:
            self.stdout.write(self.style.SUCCESS(f'Trained LBPH model on {trained} employees.'))
        else:
            self.stdout.write(self.style.ERROR('No faces detected in employee photos.'))
