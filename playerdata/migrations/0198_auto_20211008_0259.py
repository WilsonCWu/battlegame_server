# Generated by Django 3.0.4 on 2021-10-08 02:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0197_inventory_login_chest'),
    ]

    operations = [
        migrations.RenameField(
            model_name='dailydungeonstatus',
            old_name='tier',
            new_name='cur_tier',
        ),
        migrations.AddField(
            model_name='dailydungeonstatus',
            name='furthest_tier',
            field=models.IntegerField(default=0),
        ),
    ]
