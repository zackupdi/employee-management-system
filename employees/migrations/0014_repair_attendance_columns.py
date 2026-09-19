from django.db import migrations


def add_missing_attendance_columns(apps, schema_editor):
    connection = schema_editor.connection
    table = 'employees_attendance'
    columns = {
        column.name for column in connection.introspection.get_table_description(
            connection.cursor(), table
        )
    }
    with connection.cursor() as cursor:
        if 'check_in' not in columns:
            cursor.execute('ALTER TABLE employees_attendance ADD COLUMN check_in time NULL')
        if 'check_out' not in columns:
            cursor.execute('ALTER TABLE employees_attendance ADD COLUMN check_out time NULL')


def remove_repaired_columns(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0013_attendance_check_in_check_out_status'),
    ]

    operations = [
        migrations.RunPython(add_missing_attendance_columns, remove_repaired_columns),
    ]
