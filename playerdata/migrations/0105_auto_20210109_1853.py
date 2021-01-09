# Generated by Django 3.0.4 on 2021-01-09 18:53

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0104_baseprestige'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basecharacter',
            name='rarity',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(4)]),
        ),
        migrations.AlterField(
            model_name='baseprestige',
            name='level',
            field=models.IntegerField(),
        ),
    ]
