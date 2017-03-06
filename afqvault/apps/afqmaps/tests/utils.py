from afqvault.apps.afqmaps.forms import AFQMapForm, AtlasForm
from afqvault.apps.afqmaps.models import Collection, Image
from django.core.files.uploadedfile import SimpleUploadedFile
from afqvault.settings import PRIVATE_MEDIA_ROOT
import shutil
import os


def clearDB():
    Image.objects.all().delete()
    Collection.objects.all().delete()
    if os.path.exists(PRIVATE_MEDIA_ROOT):
        for the_file in os.listdir(PRIVATE_MEDIA_ROOT):
            file_path = os.path.join(PRIVATE_MEDIA_ROOT, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception, e:
                print e


def save_statmap_form(image_path, collection, ignore_file_warning=False, image_name=None):

    if image_name is None:
        if isinstance(image_path, list):
            image_name = image_path[0]
        else:
            image_name = image_path

    post_dict = {
        'name': image_name,
        'modality': 'fMRI-BOLD',
        'map_type': 'T',
        'collection': collection.pk,
        'ignore_file_warning': ignore_file_warning
    }
    # If image path is a list, we have img/hdr
    if isinstance(image_path, list):
        file_dict = {'file': SimpleUploadedFile(image_path[0], open(image_path[0]).read()),
                     'hdr_file': SimpleUploadedFile(image_path[1], open(image_path[1]).read())}
    else:
        file_dict = {'file': SimpleUploadedFile(
            image_path, open(image_path).read())}
    form = AFQMapForm(post_dict, file_dict)
    # this is necessary to split 4D volumes
    form.is_valid()
    return form.save()


def save_atlas_form(nii_path, xml_path, collection, ignore_file_warning=False, name=None):

    if name is None:
        name = nii_path

    post_dict = {
        'name': name,
        'map_type': 'Atlas',
        'collection': collection.pk,
        'ignore_file_warning': ignore_file_warning
    }
    file_dict = {'file': SimpleUploadedFile(nii_path, open(nii_path).read()),
                 'label_description_file': SimpleUploadedFile(xml_path, open(xml_path).read())}
    form = AtlasForm(post_dict, file_dict)
    return form.save()
