# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import taggit.managers
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('afqmaps', '0060_auto_20160103_0406'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseCollectionItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200, db_index=True)),
                ('description', models.TextField(blank=True)),
                ('add_date', models.DateTimeField(auto_now_add=True, verbose_name=b'date published')),
                ('modify_date', models.DateTimeField(auto_now=True, verbose_name=b'date modified')),
                ('collection', models.ForeignKey(to='afqmaps.Collection')),
                ('polymorphic_ctype', models.ForeignKey(related_name='polymorphic_afqmaps.basecollectionitem_set+', editable=False, to='contenttypes.ContentType', null=True)),
                ('tags', taggit.managers.TaggableManager(to='afqmaps.KeyValueTag', through='afqmaps.ValueTaggedItem', blank=True, help_text='A comma-separated list of tags.', verbose_name='Tags')),
            ],
        ),
        migrations.AddField(
            model_name='image',
            name='basecollectionitem_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, null=True, serialize=False, to='afqmaps.BaseCollectionItem'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='nidmresults',
            name='basecollectionitem_ptr',
            field=models.OneToOneField(parent_link=True, auto_created=True, null=True, serialize=False, to='afqmaps.BaseCollectionItem'),
            preserve_default=False,
        ),
    ]
