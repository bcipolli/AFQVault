# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import afqvault.apps.afqmaps.models
import afqvault.apps.afqmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0071_auto_20160903_1114'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='surface_left_file',
            field=models.FileField(storage=afqvault.apps.afqmaps.storage.DoubleExtensionStorage(), upload_to=afqvault.apps.afqmaps.models.upload_img_to, null=True, verbose_name=b'File with the unthresholded left hemisphere fsaverage surface map (.mgh)', blank=True),
        ),
        migrations.AddField(
            model_name='image',
            name='surface_right_file',
            field=models.FileField(storage=afqvault.apps.afqmaps.storage.DoubleExtensionStorage(), upload_to=afqvault.apps.afqmaps.models.upload_img_to, null=True, verbose_name=b'File with the unthresholded right hemisphere fsaverage surface map (.mgh)', blank=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='file',
            field=models.FileField(upload_to=afqvault.apps.afqmaps.models.upload_img_to, storage=afqvault.apps.afqmaps.storage.DoubleExtensionStorage(), verbose_name=b'File with the unthresholded volume map (.img, .nii, .nii.gz)'),
        ),
    ]
