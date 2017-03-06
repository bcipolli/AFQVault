# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import taggit.managers
from django.db import migrations, models

def fix_foreign_keys(apps, schema_editor):
    NIDMResultStatisticMap = apps.get_model("afqmaps", "NIDMResultStatisticMap")
    NIDMResults = apps.get_model("afqmaps", "NIDMResults")

    for nidmresultmap in NIDMResultStatisticMap.objects.all():
        nidmresultmap.nidm_results_id = NIDMResults.objects.get(old_id=nidmresultmap.nidm_results_id).pk
        nidmresultmap.save()


class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0063_remove_old_fields'),
    ]

    operations = [
        migrations.RunPython(fix_foreign_keys),
        migrations.RemoveField(
            model_name='nidmresults',
            name='old_id',
        ),
    ]
