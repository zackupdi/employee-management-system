from django.db import migrations


def assign_legacy_records(apps, schema_editor):
    Business = apps.get_model('employees', 'Business')
    BusinessMembership = apps.get_model('employees', 'BusinessMembership')
    WorkSchedule = apps.get_model('employees', 'WorkSchedule')
    Employee = apps.get_model('employees', 'Employee')
    Attendance = apps.get_model('employees', 'Attendance')

    business, _ = Business.objects.get_or_create(
        name='Default Business',
        defaults={'location': '', 'timezone': 'UTC'},
    )
    schedule, _ = WorkSchedule.objects.get_or_create(
        business=business,
        name='Default schedule',
        defaults={
            'work_start': '08:00',
            'checkin_window_end': '08:30',
            'work_end': '16:00',
            'grace_minutes': 0,
            'timezone': 'UTC',
            'workdays': '0,1,2,3,4',
        },
    )
    Employee.objects.filter(business__isnull=True).update(
        business=business,
        assigned_schedule=schedule,
    )
    Attendance.objects.filter(business__isnull=True).update(
        business=business,
        schedule=schedule,
    )
    User = apps.get_model('auth', 'User')
    for user in User.objects.filter(is_staff=True):
        BusinessMembership.objects.get_or_create(
            user=user,
            business=business,
            defaults={'role': 'SUPER_ADMIN', 'is_active': True},
        )


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0017_business_multitenant_attendance'),
    ]

    operations = [
        migrations.RunPython(assign_legacy_records, migrations.RunPython.noop),
    ]
