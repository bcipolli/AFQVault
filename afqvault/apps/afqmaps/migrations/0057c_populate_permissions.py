# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from guardian.shortcuts import assign_perm
from django.db import migrations
from django.contrib.auth import get_user_model

def populate_permissions(apps, schema_editor):
    Collection = apps.get_model("afqmaps", "Collection")
    User = get_user_model()
    for collection in Collection.objects.all():
        user = User.objects.get(pk=collection.owner.pk)
        assign_perm('afqmaps.delete_collection', user, collection)

        for contributor in [collection.owner, ] + list(collection.contributors.all()):
            user = User.objects.get(pk=contributor.pk)
            assign_perm('afqmaps.change_collection', user, collection)
            for image in collection.image_set.all():
                assign_perm('afqmaps.change_image', user, image)
                assign_perm('afqmaps.delete_image', user, image)
            for nidmresult in collection.nidmresults_set.all():
                assign_perm('afqmaps.change_nidmresults', user, nidmresult)
                assign_perm('afqmaps.delete_nidmresults', user, nidmresult)

class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0056_auto_20151023_1807'),
    ]

    operations = [
        migrations.RunPython(populate_permissions),
    ]
