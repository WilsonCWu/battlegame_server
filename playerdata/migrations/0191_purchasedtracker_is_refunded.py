# Generated by Django 3.0.4 on 2021-09-24 15:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0190_auto_20210923_1733'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchasedtracker',
            name='is_refunded',
            field=models.BooleanField(default=False),
        ),
    ]