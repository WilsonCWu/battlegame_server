# Generated by Django 3.0.4 on 2021-03-15 20:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0127_userstats_chest_counter'),
    ]

    operations = [
        migrations.AddField(
            model_name='invalidreceipt',
            name='receipt',
            field=models.TextField(default=''),
        ),
    ]
