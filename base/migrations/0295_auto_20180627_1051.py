# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2018-06-27 08:51
from __future__ import unicode_literals

import ckeditor.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0294_auto_20180625_1159'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Bibliography',
            new_name='TeachingMaterial',
        ),
        migrations.AddField(
            model_name='learningunityear',
            name='bibliography',
            field=ckeditor.fields.RichTextField(blank=True, null=True, verbose_name='bibliography'),
        ),
    ]
