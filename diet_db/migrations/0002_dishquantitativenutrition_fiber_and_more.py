# Generated by Django 4.1.4 on 2022-12-14 17:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diet_db', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dishquantitativenutrition',
            name='fiber',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dishquantitativenutrition',
            name='sugars',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
