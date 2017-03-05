import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "afqvault.settings")
django.setup()

from afqvault.apps.statmaps.models import Image, BaseStatisticMap


# Now, we need to generate a "comparison" object for all files in the database
# We will use a celery task (as this will be integrated into upload workflow)
for image in Image.objects.all():
    if isinstance(image, BaseStatisticMap):
        image.save()