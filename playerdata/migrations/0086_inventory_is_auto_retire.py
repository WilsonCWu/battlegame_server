# Generated by Django 3.0.4 on 2020-11-23 07:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0085_inventory_essence'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventory',
            name='is_auto_retire',
            field=models.BooleanField(default=False),
        ),
    ]
