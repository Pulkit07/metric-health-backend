# Generated by Django 4.1.4 on 2023-04-03 14:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('watch_sdk', '0041_userapp_debug_store_webhook_logs'),
    ]

    operations = [
        migrations.CreateModel(
            name='DebugIosData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('data', models.JSONField()),
                ('uuid', models.CharField(blank=True, max_length=100, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
