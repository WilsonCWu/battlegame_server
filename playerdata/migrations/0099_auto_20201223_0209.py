# Generated by Django 3.0.4 on 2020-12-23 02:09

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0098_auto_20201220_1650'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchasedtracker',
            name='purchase_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='purchasedtracker',
            name='transaction_id',
            field=models.TextField(default=''),
        ),
    ]