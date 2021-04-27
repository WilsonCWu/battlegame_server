# Generated by Django 3.0.4 on 2021-04-27 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0146_auto_20210427_0607'),
    ]

    operations = [
        migrations.RenameField(
            model_name='match',
            old_name='attacker_elo',
            new_name='original_attacker_elo',
        ),
        migrations.RenameField(
            model_name='match',
            old_name='defender_elo',
            new_name='original_defender_elo',
        ),
        migrations.AddField(
            model_name='match',
            name='updated_attacker_elo',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='match',
            name='updated_defender_elo',
            field=models.IntegerField(default=0),
        ),
    ]
