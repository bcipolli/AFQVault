# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0036_auto_20150305_1846'),
    ]

    operations = [
        migrations.AddField(
            model_name='afqmap',
            name='brain_coverage',
            field=models.FloatField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='afqmap',
            name='not_mni',
            field=models.NullBooleanField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='afqmap',
            name='perc_voxels_outside',
            field=models.FloatField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='afqmap',
            name='ignore_file_warning',
            field=models.BooleanField(default=False, help_text=b'Ignore the warning when the map is sparse by nature, an ROI mask, or was acquired with limited field of view.', verbose_name=b'Ignore the warning'),
            preserve_default=True,
        ),
    ]
