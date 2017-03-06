import os
from gzip import GzipFile

import django
import nibabel as nb

import afqvault.apps.afqmaps.utils as nvutils
from afqvault.apps.afqmaps.models import AFQMap, BaseAFQMap

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "afqvault.settings")
django.setup()

for image in AFQMap.objects.filter(map_type=BaseAFQMap.OTHER):
    image.file.open()
    gzfileobj = GzipFile(filename=image.file.name, mode='rb', fileobj=image.file.file)
    nii = nb.Nifti1Image.from_file_map({'image': nb.FileHolder(image.file.name, gzfileobj)})
    map_type = nvutils.infer_map_type(nii)
    if map_type != BaseAFQMap.OTHER:
        print "changed type of %s to %s"%(image.get_absolute_url(), map_type)
        image.map_type = map_type
        image.save()
    image.file.close()
