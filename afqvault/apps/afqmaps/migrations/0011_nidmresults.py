# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import afqvault.apps.afqmaps.models
import afqvault.apps.afqmaps.storage


class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0010_atlas'),
    ]

    operations = [
        migrations.CreateModel(
            name='NIDMResults',
            fields=[
                ('image_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='afqmaps.Image')),
                ('ttl_file', models.FileField(upload_to=afqvault.apps.afqmaps.models.upload_to, storage=afqvault.apps.afqmaps.storage.DoubleExtensionStorage(), verbose_name=b'Turtle serialization of NIDM Results (.ttl)')),
            ],
            options={
                'abstract': False,
            },
            bases=('afqmaps.image',),
        ),
    ]
