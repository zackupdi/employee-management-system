from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('employees', '0016_ensure_attendance_columns'),
    ]

    operations = [
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('location', models.CharField(blank=True, max_length=255)),
                ('timezone', models.CharField(default='UTC', max_length=64)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='BusinessMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('SUPER_ADMIN', 'Super Admin'), ('MANAGER', 'Manager'), ('EMPLOYEE', 'Employee')], default='EMPLOYEE', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='employees.business')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='business_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={'constraints': [models.UniqueConstraint(fields=('user', 'business'), name='unique_business_membership')]},
        ),
        migrations.CreateModel(
            name='KioskDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('device_id', models.CharField(max_length=100, unique=True)),
                ('token_hash', models.CharField(max_length=128)),
                ('is_active', models.BooleanField(default=True)),
                ('last_seen_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kiosks', to='employees.business')),
            ],
        ),
        migrations.CreateModel(
            name='WorkSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Default schedule', max_length=100)),
                ('work_start', models.TimeField(default='08:00')),
                ('checkin_window_end', models.TimeField(default='08:30')),
                ('work_end', models.TimeField(default='16:00')),
                ('grace_minutes', models.PositiveIntegerField(default=0)),
                ('timezone', models.CharField(default='UTC', max_length=64)),
                ('workdays', models.CharField(default='0,1,2,3,4', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='employees.business')),
            ],
        ),
        migrations.AddField(
            model_name='employee', name='business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employees', to='employees.business'),
        ),
        migrations.AddField(model_name='employee', name='email', field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name='employee', name='employee_number', field=models.CharField(blank=True, max_length=50, null=True)),
        migrations.AddField(model_name='employee', name='employment_start_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='employee', name='employment_status', field=models.CharField(default='Active', max_length=30)),
        migrations.AddField(model_name='employee', name='face_enrolled_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='employee', name='phone', field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name='employee', name='position', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='employee', name='workplace', field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name='employee', name='user', field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employee_profile', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='employee', name='assigned_schedule', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employees', to='employees.workschedule')),
        migrations.AddField(model_name='attendance', name='attendance_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='attendance', name='business', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_records', to='employees.business')),
        migrations.AddField(model_name='attendance', name='check_in_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='attendance', name='check_out_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='attendance', name='late_minutes', field=models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
        migrations.AddField(model_name='attendance', name='verification_method', field=models.CharField(default='face', max_length=30)),
        migrations.AddField(model_name='attendance', name='verification_score', field=models.FloatField(blank=True, null=True)),
        migrations.AddField(model_name='attendance', name='created_at', field=models.DateTimeField(auto_now_add=True)),
        migrations.AddField(model_name='attendance', name='updated_at', field=models.DateTimeField(auto_now=True)),
        migrations.AddField(model_name='attendance', name='schedule', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_records', to='employees.workschedule')),
        migrations.AddField(model_name='attendance', name='kiosk', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='attendance_records', to='employees.kioskdevice')),
        migrations.CreateModel(
            name='FaceEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('embedding', models.BinaryField()),
                ('algorithm', models.CharField(default='opencv-lbph', max_length=50)),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='face_enrollments', to='employees.business')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='face_enrollments', to='employees.employee')),
                ('enrolled_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AttendanceAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=50)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('attendance', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='employees.attendance')),
                ('business', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='employees.business')),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='employees.employee')),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='employee',
            constraint=models.UniqueConstraint(fields=('business', 'employee_number'), name='unique_business_employee_number'),
        ),
    ]
