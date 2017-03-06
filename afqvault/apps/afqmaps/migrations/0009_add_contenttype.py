# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def add_contenttype(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    AFQMap = apps.get_model("afqmaps", "AFQMap")
    for statisticmap in AFQMap.objects.all():
        statisticmap.polymorphic_ctype = ContentType.objects.get(model='afqmap', app_label='afqmaps')
        statisticmap.save()

class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0008_polymorphism'),
    ]

    operations = [
        migrations.RunPython(add_contenttype),
    ]
