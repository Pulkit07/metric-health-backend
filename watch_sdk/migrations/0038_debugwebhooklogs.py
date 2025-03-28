# Generated by Django 4.1.4 on 2023-03-20 10:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('watch_sdk', '0037_iosdatahashlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='DebugWebhookLogs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('data', models.JSONField()),
                ('uuid', models.CharField(blank=True, max_length=100, null=True)),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='watch_sdk.userapp')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
