# Generated by Django 4.1.4 on 2023-02-04 09:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('watch_sdk', '0019_alter_userapp_enabled_platforms'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='watchconnection',
            name='google_fit_email',
        ),
        migrations.RemoveField(
            model_name='watchconnection',
            name='google_fit_refresh_token',
        ),
        migrations.RemoveField(
            model_name='watchconnection',
            name='last_modified',
        ),
        migrations.RemoveField(
            model_name='watchconnection',
            name='last_sync',
        ),
    ]
