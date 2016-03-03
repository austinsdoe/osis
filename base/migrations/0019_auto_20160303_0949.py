# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-03-03 08:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0018_auto_20160226_1138'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='academiccalendar',
            name='event_type',
        ),
        migrations.RemoveField(
            model_name='offeryearcalendar',
            name='event_type',
        ),
        migrations.AddField(
            model_name='academicyear',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='academicyear',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
