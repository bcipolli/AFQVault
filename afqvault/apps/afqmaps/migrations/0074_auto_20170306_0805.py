# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import afqvault.apps.afqmaps.models
import afqvault.apps.afqmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0073_auto_20161111_0033'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cognitiveatlascontrast',
            name='task',
        ),
        migrations.RemoveField(
            model_name='nidmresultafqmap',
            name='image_ptr',
        ),
        migrations.RemoveField(
            model_name='nidmresultafqmap',
            name='nidm_results',
        ),
        migrations.RemoveField(
            model_name='nidmresults',
            name='basecollectionitem_ptr',
        ),
        migrations.RemoveField(
            model_name='afqmap',
            name='cognitive_contrast_cogatlas',
        ),
        migrations.RemoveField(
            model_name='afqmap',
            name='cognitive_paradigm_cogatlas',
        ),
        migrations.RemoveField(
            model_name='afqmap',
            name='cognitive_paradigm_description_url',
        ),
        migrations.RemoveField(
            model_name='afqmap',
            name='contrast_definition',
        ),
        migrations.RemoveField(
            model_name='afqmap',
            name='contrast_definition_cogatlas',
        ),
        migrations.RemoveField(
            model_name='image',
            name='surface_left_file',
        ),
        migrations.RemoveField(
            model_name='image',
            name='surface_right_file',
        ),
        migrations.AlterField(
            model_name='afqmap',
            name='analysis_level',
            field=models.CharField(choices=[(b'Single', b'single-subject'), (b'Group', b'group'), (b'Meta', b'meta-analysis'), (b'Other', b'other')], max_length=200,
                                   blank=True, help_text=b'What level of summary data was used as the input to this analysis?', null=True, verbose_name=b'Analysis level'),
        ),
        migrations.AlterField(
            model_name='afqmap',
            name='map_type',
            field=models.CharField(help_text=b'Type of statistic that is the basis of the inference',
                                   max_length=200, verbose_name=b'Map type', choices=[(b'AFQ', b'AFQ map'), (b'Other', b'other')]),
        ),
        migrations.AlterField(
            model_name='afqmap',
            name='modality',
            field=models.CharField(help_text=b'Brain imaging procedure that was used to acquire the data.', max_length=200,
                                   verbose_name=b'Modality & Acquisition Type', choices=[(b'Diffusion MRI', b'Diffusion MRI'), (b'Other', b'Other')]),
        ),
        migrations.AlterField(
            model_name='collection',
            name='private',
            field=models.BooleanField(default=False, verbose_name=b'Accessibility', choices=[(False, b'Public (The collection will be accessible by anyone and all the data in it will be distributed under CC0 license)'), (
                True, b'Private (The collection will be not listed in the AFQVault index. It will be possible to shared it with others at a private URL.)')]),
        ),
        migrations.AlterField(
            model_name='image',
            name='file',
            field=models.FileField(upload_to=afqvault.apps.afqmaps.models.upload_img_to,
                                   storage=afqvault.apps.afqmaps.storage.DoubleExtensionStorage(), verbose_name=b'File with AFQ result (.mat)'),
        ),
        migrations.DeleteModel(
            name='CognitiveAtlasContrast',
        ),
        migrations.DeleteModel(
            name='CognitiveAtlasTask',
        ),
        migrations.DeleteModel(
            name='NIDMResultAFQMap',
        ),
        migrations.DeleteModel(
            name='NIDMResults',
        ),
    ]
