# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2017-04-10 11:22
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('internship', '0045_auto_20170407_1358'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cohort',
            options={'ordering': ['name']},
        ),
    ]
