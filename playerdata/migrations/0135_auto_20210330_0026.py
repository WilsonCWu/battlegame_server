# Generated by Django 3.0.4 on 2021-03-30 00:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0134_dungeonboss_carry_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='moevasionstatus',
            name='damage',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='userinfo',
            name='best_moevasion_stage',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name='userinfo',
            index=models.Index(fields=['best_moevasion_stage'], name='playerdata__best_mo_b35a7d_idx'),
        ),
    ]