# Generated by Django 3.0.4 on 2021-03-09 15:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0122_basecharacterability2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventory',
            name='daily_dungeon_golden_ticket',
            field=models.IntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='inventory',
            name='daily_dungeon_ticket',
            field=models.IntegerField(default=3),
        ),
    ]