# Generated by Django 3.0.4 on 2021-09-10 19:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0185_mail_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='mail',
            name='has_unclaimed_reward',
            field=models.BooleanField(default=False),
        ),
    ]
