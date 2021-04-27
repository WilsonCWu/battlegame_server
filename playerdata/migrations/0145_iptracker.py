# Generated by Django 3.0.4 on 2021-04-27 00:55

from django.db import migrations, models
import django_better_admin_arrayfield.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('playerdata', '0144_clanmember_is_elder'),
    ]

    operations = [
        migrations.CreateModel(
            name='IPTracker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.TextField(unique=True)),
                ('user_list', django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.TextField(), blank=True, default=list, null=True, size=None)),
                ('suspicious', models.BooleanField(default=False)),
            ],
        ),
    ]
