# Generated by Django 3.0.4 on 2021-09-09 20:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0184_rogueallowedabilities_is_passive'),
    ]

    operations = [
        migrations.AddField(
            model_name='mail',
            name='title',
            field=models.TextField(default=''),
        ),
    ]