# Generated by Django 3.0.4 on 2021-01-05 21:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0102_auto_20210104_0123'),
    ]

    operations = [
        migrations.AlterField(
            model_name='character',
            name='total_damage_dealt',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='character',
            name='total_damage_taken',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='character',
            name='total_health_healed',
            field=models.BigIntegerField(default=0),
        ),
    ]
