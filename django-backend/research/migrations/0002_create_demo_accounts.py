from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_demo_researcher(apps, schema_editor):
    User = apps.get_model('auth', 'User')

    # Ensure demo_researcher account with AeroVital2026!
    user, _ = User.objects.get_or_create(
        username='demo_researcher',
        defaults={
            'email': 'demo_researcher@aerovital.internal',
            'first_name': 'Demo',
            'last_name': 'Researcher',
            'is_staff': True,
            'is_active': True,
        }
    )
    user.password = make_password('AeroVital2026!')
    user.is_active = True
    user.save()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('research', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_demo_researcher, noop_reverse),
    ]
