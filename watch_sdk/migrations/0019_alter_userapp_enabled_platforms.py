# Generated by Django 4.1.4 on 2023-02-02 11:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('watch_sdk', '0018_alter_enabledplatform_platform_app_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userapp',
            name='enabled_platforms',
            field=models.ManyToManyField(blank=True, null=True, to='watch_sdk.enabledplatform'),
        ),
    ]
