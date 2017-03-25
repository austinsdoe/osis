# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-09-05 09:13
from __future__ import unicode_literals
from django.core.exceptions import FieldDoesNotExist
from django.db import migrations, models
import uuid


def set_uuids_model(apps, model):
    internship = apps.get_app_config('internship')
    model_class = internship.get_model(model)
    ids = model_class.objects.values_list('id', flat=True)
    if ids:
        for pk in ids:
            try:
                model_class.objects.filter(pk=pk).update(uuid=uuid.uuid4())
            except FieldDoesNotExist:
                break


def set_uuid_field(apps, schema_editor):
    set_uuids_model(apps, "periodinternshipplaces")



class Migration(migrations.Migration):

    dependencies = [
        ('internship', '0031_add_uuid_field_period_places'),
    ]

    operations = [
        migrations.RunPython(set_uuid_field),

        migrations.AlterField(
            model_name='periodinternshipplaces',
            name='uuid',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
