# Generated by Django 3.0.4 on 2020-04-05 18:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0012_auto_20200405_1856'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='team',
            name='pos_1',
        ),
        migrations.RemoveField(
            model_name='team',
            name='pos_2',
        ),
        migrations.RemoveField(
            model_name='team',
            name='pos_3',
        ),
        migrations.RemoveField(
            model_name='team',
            name='pos_4',
        ),
        migrations.RemoveField(
            model_name='team',
            name='pos_5',
        ),
        migrations.RemoveField(
            model_name='team',
            name='pos_6',
        ),
    ]
