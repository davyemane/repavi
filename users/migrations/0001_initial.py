from django.db import migrations

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunSQL("SELECT 1;", reverse_sql="SELECT 1;"),
    ]
