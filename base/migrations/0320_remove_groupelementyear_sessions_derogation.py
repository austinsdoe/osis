# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2018-07-27 07:41
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0319_auto_20180727_0837'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='groupelementyear',
            name='sessions_derogation',
        ),
    ]
