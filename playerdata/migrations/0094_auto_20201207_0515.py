# Generated by Django 3.0.4 on 2020-12-07 05:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0093_auto_20201206_0117'),
    ]

    operations = [
        migrations.AddField(
            model_name='basecharacterability',
            name='ability1_desc',
            field=models.CharField(default='', max_length=250),
        ),
        migrations.AddField(
            model_name='basecharacterability',
            name='ability2_desc',
            field=models.CharField(default='', max_length=250),
        ),
        migrations.AddField(
            model_name='basecharacterability',
            name='ability3_desc',
            field=models.CharField(default='', max_length=250),
        ),
        migrations.AddField(
            model_name='basecharacterability',
            name='ultimate_desc',
            field=models.CharField(default='', max_length=250),
        ),
    ]