# Generated by Django 4.1.4 on 2023-03-01 11:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('watch_sdk', '0032_connectedplatformmetadata_connection'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='watchconnection',
            name='connected_platforms',
        ),
        migrations.AlterField(
            model_name='connectedplatformmetadata',
            name='connection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='watch_sdk.watchconnection'),
        ),
    ]
