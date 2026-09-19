from django.db import migrations, models


def normalize_salary_request_statuses(apps, schema_editor):
    SalaryRequest = apps.get_model('employees', 'SalaryRequest')
    SalaryRequest.objects.filter(status='Pending').update(status='pending')
    SalaryRequest.objects.filter(status='Approved').update(status='accepted')
    SalaryRequest.objects.filter(status='Rejected').update(status='rejected')


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0020_salaryrequest_amount_salaryrequest_business_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_salary_request_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='salaryrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending Review'),
                    ('accepted', 'Accepted'),
                    ('rejected', 'Rejected'),
                    ('processed', 'Processed'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='salaryrequest',
            name='processed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]