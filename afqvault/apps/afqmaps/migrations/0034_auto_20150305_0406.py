# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0033_statisticmap_ignore_file_warning'),
    ]

    operations = [
        migrations.AddField(
            model_name='afqmap',
            name='is_thresholded',
            field=models.NullBooleanField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='afqmap',
            name='perc_bad_voxels',
            field=models.FloatField(null=True),
            preserve_default=True,
        ),
    ]
