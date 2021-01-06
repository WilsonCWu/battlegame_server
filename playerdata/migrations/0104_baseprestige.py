# Generated by Django 3.0.4 on 2021-01-05 22:55

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_better_admin_arrayfield.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0103_auto_20210105_2122'),
    ]

    operations = [
        migrations.CreateModel(
            name='BasePrestige',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attack_flat', models.IntegerField(blank=True, null=True)),
                ('attack_mult', models.FloatField(blank=True, null=True)),
                ('ability_flat', models.IntegerField(blank=True, null=True)),
                ('ability_mult', models.FloatField(blank=True, null=True)),
                ('attack_speed_mult', models.FloatField(blank=True, null=True)),
                ('ar_flat', models.IntegerField(blank=True, null=True)),
                ('ar_mult', models.FloatField(blank=True, null=True)),
                ('mr_flat', models.IntegerField(blank=True, null=True)),
                ('mr_mult', models.FloatField(blank=True, null=True)),
                ('speed_flat', models.IntegerField(blank=True, null=True)),
                ('speed_mult', models.FloatField(blank=True, null=True)),
                ('crit_flat', models.IntegerField(blank=True, null=True)),
                ('crit_mult', models.FloatField(blank=True, null=True)),
                ('mana_tick_flat', models.IntegerField(blank=True, null=True)),
                ('mana_tick_mult', models.FloatField(blank=True, null=True)),
                ('range_flat', models.IntegerField(blank=True, null=True)),
                ('max_health_flat', models.IntegerField(blank=True, null=True)),
                ('max_health_mult', models.FloatField(blank=True, null=True)),
                ('effect_ids', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.IntegerField(), blank=True, null=True, size=None)),
                ('level', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)])),
                ('char_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.BaseCharacter')),
            ],
            options={
                'unique_together': {('char_type', 'level')},
            },
        ),
    ]
