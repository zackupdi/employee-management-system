from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0018_assign_legacy_records'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalaryPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period', models.CharField(help_text='Format: YYYY-MM, e.g. 2026-09', max_length=7)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('date_paid', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='salary_payments', to='employees.employee')),
            ],
            options={
                'ordering': ['-period'],
                'constraints': [models.UniqueConstraint(fields=('employee', 'period'), name='unique_employee_salary_period')],
            },
        ),
    ]
