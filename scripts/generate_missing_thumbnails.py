import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "afqvault.settings")
django.setup()

from afqvault.apps.afqmaps.models import AFQMap
from afqvault.apps.afqmaps.tasks import generate_glassbrain_image,\
    save_resampled_transformation_single

for image in AFQMap.objects.filter(collection__private=False).exclude(analysis_level = 'S').exclude(is_thresholded = True):
    print image.id
    generate_glassbrain_image.apply_async([image.id])
    save_resampled_transformation_single.apply_async([image.id])
