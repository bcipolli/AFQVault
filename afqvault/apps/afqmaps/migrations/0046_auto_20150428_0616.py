# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import afqvault.apps.afqmaps.models
import afqvault.apps.afqmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0045_auto_20150428_0229'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='reduced_representation',
            field=models.FileField(storage=afqvault.apps.afqmaps.storage.OverwriteStorage(), upload_to=afqvault.apps.afqmaps.models.upload_img_to, blank=True, help_text=b'Binary file with the vector of in brain values resampled to lower resolution', null=True, verbose_name=b'Reduced representation of the image'),
            preserve_default=True,
        ),
    ]
