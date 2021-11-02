# Generated by Django 3.0.4 on 2021-11-02 18:42

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import playerdata.models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0208_eventtimetracker'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dungeonboss',
            name='team_comp',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, validators=[playerdata.models.validate_placement_json]),
        ),
        migrations.AlterField(
            model_name='placement',
            name='pos_1',
            field=models.IntegerField(default=-1, validators=[playerdata.models.validate_position]),
        ),
        migrations.AlterField(
            model_name='placement',
            name='pos_2',
            field=models.IntegerField(default=-1, validators=[playerdata.models.validate_position]),
        ),
        migrations.AlterField(
            model_name='placement',
            name='pos_3',
            field=models.IntegerField(default=-1, validators=[playerdata.models.validate_position]),
        ),
        migrations.AlterField(
            model_name='placement',
            name='pos_4',
            field=models.IntegerField(default=-1, validators=[playerdata.models.validate_position]),
        ),
        migrations.AlterField(
            model_name='placement',
            name='pos_5',
            field=models.IntegerField(default=-1, validators=[playerdata.models.validate_position]),
        ),
    ]