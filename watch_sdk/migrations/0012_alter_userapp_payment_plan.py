# Generated by Django 4.1.4 on 2023-01-10 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('watch_sdk', '0011_userapp_payment_plan'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userapp',
            name='payment_plan',
            field=models.CharField(choices=[('free', 'free'), ('startup', 'startup'), ('enterprise', 'enterprise')], default='free', max_length=100),
        ),
    ]
