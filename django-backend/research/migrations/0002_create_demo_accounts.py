import os
from django.db import migrations
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ImproperlyConfigured


def create_demo_researcher(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    username = 'demo_researcher'

    # Check whether demo_researcher already exists
    if User.objects.filter(username=username).exists():
        # Account exists: preserve all existing fields and credentials untouched
        return

    # Account does not exist: obtain initial password exclusively from environment variable
    raw_password = os.environ.get('DEMO_RESEARCHER_PASSWORD')
    if not raw_password or not raw_password.strip():
        raise ImproperlyConfigured(
            "Cannot create demo_researcher account: DEMO_RESEARCHER_PASSWORD environment variable "
            "is missing or empty. Please set DEMO_RESEARCHER_PASSWORD before running migrations."
        )

    # Create new account with no staff/superuser privileges and hashed password
    User.objects.create(
        username=username,
        email='demo_researcher@aerovital.internal',
        first_name='Demo',
        last_name='Researcher',
        password=make_password(raw_password),
        is_staff=False,
        is_superuser=False,
        is_active=True,
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('research', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_demo_researcher, noop_reverse),
    ]
