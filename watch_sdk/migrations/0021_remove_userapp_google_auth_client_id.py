# Generated by Django 4.1.4 on 2023-02-04 12:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('watch_sdk', '0020_remove_watchconnection_google_fit_email_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userapp',
            name='google_auth_client_id',
        ),
    ]
