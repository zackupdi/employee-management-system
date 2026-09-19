from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0012_employee_face_encoding_employee_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='check_in',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='check_out',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='status',
            field=models.CharField(default='Present', max_length=10),
        ),
        migrations.AlterUniqueTogether(
            name='attendance',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='attendance',
            constraint=models.UniqueConstraint(fields=('employee', 'date'), name='unique_employee_attendance_day'),
        ),
    ]
