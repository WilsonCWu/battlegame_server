# Generated by Django 3.0.4 on 2021-04-28 22:09

from django.db import migrations, models
import django_better_admin_arrayfield.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0148_auto_20210428_1809'),
    ]

    operations = [
        migrations.AlterField(
            model_name='iptracker',
            name='user_list',
            field=django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.IntegerField(), blank=True, default=list, null=True, size=None),
        ),
    ]