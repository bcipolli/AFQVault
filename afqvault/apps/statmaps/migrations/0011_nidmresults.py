# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import afqvault.apps.statmaps.models
import afqvault.apps.statmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('statmaps', '0010_atlas'),
    ]

    operations = [
        migrations.CreateModel(
            name='NIDMResults',
            fields=[
                ('image_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='statmaps.Image')),
                ('ttl_file', models.FileField(upload_to=afqvault.apps.statmaps.models.upload_to, storage=afqvault.apps.statmaps.storage.DoubleExtensionStorage(), verbose_name=b'Turtle serialization of NIDM Results (.ttl)')),
            ],
            options={
                'abstract': False,
            },
            bases=('statmaps.image',),
        ),
    ]
