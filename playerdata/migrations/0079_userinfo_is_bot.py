# Generated by Django 3.0.4 on 2020-11-12 21:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0078_auto_20201110_0519'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinfo',
            name='is_bot',
            field=models.BooleanField(default=False),
        ),
    ]
