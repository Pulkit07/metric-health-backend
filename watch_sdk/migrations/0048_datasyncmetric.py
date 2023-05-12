# Generated by Django 4.1.4 on 2023-05-12 11:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('watch_sdk', '0047_pendinguserinvitation'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataSyncMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('value', models.FloatField()),
                ('app', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='watch_sdk.userapp')),
                ('data_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='watch_sdk.datatype')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
