# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import afqvault.apps.afqmaps.models
import afqvault.apps.afqmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0043_auto_20150423_2059'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='thumbnail',
            field=models.FileField(storage=afqvault.apps.afqmaps.storage.DoubleExtensionStorage(), upload_to=afqvault.apps.afqmaps.models.upload_img_to, blank=True, help_text=b'The orthogonal view thumbnail path of the nifti image', null=True, verbose_name=b'Image orthogonal view thumbnail (.png)'),
            preserve_default=True,
        ),
    ]
