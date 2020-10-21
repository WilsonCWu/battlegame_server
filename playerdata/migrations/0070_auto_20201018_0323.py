# Generated by Django 3.0.4 on 2020-10-18 03:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0069_auto_20201015_2254'),
    ]

    operations = [
        migrations.AddField(
            model_name='dungeonstage',
            name='stage',
            field=models.IntegerField(null=True, unique=True),
        ),
        migrations.CreateModel(
            name='DungeonBoss',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stage', models.IntegerField()),
                ('placement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='playerdata.Placement')),
            ],
        ),
    ]
