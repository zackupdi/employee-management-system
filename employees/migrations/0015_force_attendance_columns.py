from django.db import migrations


def ensure_columns(apps, schema_editor):
    connection = schema_editor.connection
    table = 'employees_attendance'
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table)
        }
        if 'check_in' not in columns:
            cursor.execute('ALTER TABLE employees_attendance ADD COLUMN check_in time NULL')
        if 'check_out' not in columns:
            cursor.execute('ALTER TABLE employees_attendance ADD COLUMN check_out time NULL')


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0014_repair_attendance_columns'),
    ]

    operations = [
        migrations.RunPython(ensure_columns, migrations.RunPython.noop),
    ]
