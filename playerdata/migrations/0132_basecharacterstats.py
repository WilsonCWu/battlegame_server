# Generated by Django 3.0.4 on 2021-03-27 19:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0131_auto_20210327_1527'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseCharacterStats',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(default='0.0.0', max_length=30)),
                ('health', models.IntegerField()),
                ('starting_mana', models.IntegerField()),
                ('mana', models.IntegerField()),
                ('speed', models.IntegerField()),
                ('attack_damage', models.IntegerField()),
                ('ability_damage', models.IntegerField()),
                ('attack_speed', models.FloatField()),
                ('ar', models.IntegerField()),
                ('mr', models.IntegerField()),
                ('attack_range', models.IntegerField()),
                ('crit_chance', models.IntegerField()),
                ('health_scale', models.IntegerField()),
                ('attack_scale', models.IntegerField()),
                ('ability_scale', models.IntegerField()),
                ('ar_scale', models.IntegerField()),
                ('mr_scale', models.IntegerField()),
                ('char_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.BaseCharacter')),
            ],
            options={
                'unique_together': {('char_type', 'version')},
            },
        ),
    ]