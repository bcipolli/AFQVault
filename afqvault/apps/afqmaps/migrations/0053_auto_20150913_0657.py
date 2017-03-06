# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import json, os
dir = os.path.abspath(os.path.dirname(__file__))

def populate_cogatlas(apps, schema_editor):
    CognitiveAtlasTask = apps.get_model("afqmaps", "CognitiveAtlasTask")
    CognitiveAtlasContrast = apps.get_model("afqmaps", "CognitiveAtlasContrast")
    json_content = open(os.path.join(dir, "cognitiveatlas_tasks.json")).read()
    json_content = json_content.decode("utf-8").replace('\t', '')
    data = json.loads(json_content)
    for item in data:
        task, _ = CognitiveAtlasTask.objects.update_or_create(cog_atlas_id=item["id"],defaults={"name":item["name"]})
        task.save()
        for contrast in item["contrasts"]:
            conobj, _ = CognitiveAtlasContrast.objects.update_or_create(cog_atlas_id=contrast["conid"],
                                                                     defaults={"name":contrast["conname"],
                                                                               "task":task})
            conobj.save()

class Migration(migrations.Migration):

    dependencies = [
        ('afqmaps', '0052_statisticmap_cognitive_contrast_cogatlas'),
    ]

    operations = [
        migrations.RunPython(populate_cogatlas)
    ]
