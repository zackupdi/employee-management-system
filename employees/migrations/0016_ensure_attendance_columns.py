from django.db import migrations


def ensure_attendance_columns(apps, schema_editor):
    table = 'employees_attendance'
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table)
        }
        if 'check_in' not in columns:
            schema_editor.execute(
                'ALTER TABLE employees_attendance ADD COLUMN check_in time NULL'
            )
        if 'check_out' not in columns:
            schema_editor.execute(
                'ALTER TABLE employees_attendance ADD COLUMN check_out time NULL'
            )


class Migration(migrations.Migration):
    dependencies = [
        ('employees', '0015_force_attendance_columns'),
    ]

    operations = [
        migrations.RunPython(ensure_attendance_columns, migrations.RunPython.noop),
    ]