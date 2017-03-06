from __future__ import absolute_import

import nilearn
from django.core.files.base import ContentFile
from django.http import Http404
from django.shortcuts import get_object_or_404
from pybraincompare.compare.maths import calculate_correlation
from pybraincompare.compare.maths import calculate_pairwise_correlation
from pybraincompare.compare.mrutils import make_binary_deletion_mask
from pybraincompare.compare.mrutils import make_binary_deletion_vector
from pybraincompare.compare.mrutils import resample_images_ref
from pybraincompare.mr.datasets import get_data_directory
from pybraincompare.mr.transformation import make_resampled_transformation_vector

nilearn.EXPAND_PATH_WILDCARDS = False
from nilearn.plotting import plot_glass_brain
from celery import shared_task, Celery
from six import BytesIO
import nibabel as nb
import pylab as plt
import numpy
import urllib
import json
import tarfile
import requests
import os
from StringIO import StringIO
import xml.etree.cElementTree as e
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
import re
from django.conf import settings


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afqvault.settings')
app = Celery('afqvault')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(name='crawl_anima')
def crawl_anima():
    import afqvault.apps.afqmaps.models as models
    from afqvault.apps.afqmaps.forms import AFQMapForm, CollectionForm
    username = "ANIMA"
    email = "a.reid@fz-juelich.de"
    try:
        anima_user = models.User.objects.create_user(username, email)
        anima_user.save()
    except IntegrityError:
        anima_user = models.User.objects.get(username=username, email=email)

    url = "http://anima.fz-juelich.de/api/studies"
    response = urllib.urlopen(url)
    datasets = json.loads(response.read())

    # results = tarfile.open(mode="r:gz", fileobj=StringIO(response.content))
    #     for member in results.getmembers():
    #         f = results.extractfile(member)
    #         if member.name.endswith(".study"):

    for url in datasets:
        response = requests.get(url)
        content = response.content.replace("PubMed ID", "PubMedID")
        xml_obj = e.fromstring(content)

        version = xml_obj.find(".").find(".//Element[@name='Version']").text.strip()
        study_description = xml_obj.find(".//Element[@name='Description']").text.strip()
        study_description += " This dataset was automatically imported from the ANIMA <http://anima.fz-juelich.de/> database. Version: %s" % version
        study_name = xml_obj.find(".").attrib['name']

        tags = xml_obj.find(".//Element[@name='Keywords']").text.strip().split(";")
        tags.append("ANIMA")
        doi = xml_obj.find(".//Element[@name='DOI']")
        pubmedid = xml_obj.find(".//Element[@name='PubMedID']")

        post_dict = {
            'name': study_name,
            'description': study_description,
            'full_dataset_url': "http://anima.fz-juelich.de/studies/" + os.path.split(url)[1].replace(".study", "")
        }
        if doi != None:
            post_dict['DOI'] = doi.text.strip()
        elif pubmedid != None:
            pubmedid = pubmedid.text.strip()
            url = "http://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=%s&format=json" % pubmedid
            response = urllib.urlopen(url)
            parsed = json.loads(response.read())
            post_dict['DOI'] = parsed['records'][0]['doi']

        try:
            col = models.Collection.objects.get(DOI=post_dict['DOI'])
        except models.Collection.DoesNotExist:
            col = None

        if col and not col.description.endswith(version):
            col.DOI = None
            old_version = re.search(r"Version: (?P<version>\w)", col.description).group("version")
            col.name = study_name + " (version %s - deprecated)" % old_version
            col.save()

        if not col or not col.description.endswith(version):
            collection = models.Collection(owner=anima_user)
            form = CollectionForm(post_dict, instance=collection)
            form.is_valid()
            collection = form.save()

            arch_response = requests.get(url.replace("library", "library/archives").replace(".study", ".tar.gz"))
            arch_results = tarfile.open(mode="r:gz", fileobj=StringIO(arch_response.content))

            for study_element in xml_obj.findall(".//StudyElement[@type='VolumeFile']"):
                image_name = study_element.attrib['name'].strip()
                image_filename = study_element.attrib['file']
                try:
                    image_fileobject = arch_results.extractfile(xml_obj.find(".").attrib['directory'] + "/" +
                                                                image_filename)
                except KeyError:
                    image_fileobject = arch_results.extractfile(
                        xml_obj.find(".").attrib['directory'] + "/" + xml_obj.find(".").attrib['directory'] + "/" +
                        image_filename)

                map_type = models.BaseAFQMap.OTHER

                quantity_dict = {"Mask": models.BaseAFQMap.M,
                                 "F-statistic": models.BaseAFQMap.F,
                                 "T-statistic": models.BaseAFQMap.T,
                                 "Z-statistic": models.BaseAFQMap.Z,
                                 "Beta": models.BaseAFQMap.U}

                quantity = study_element.find("./Metadata/Element[@name='Quantity']")
                if quantity != None:
                    quantity = quantity.text.strip()
                    if quantity in quantity_dict.keys():
                        map_type = quantity_dict[quantity]

                post_dict = {
                    'name': image_name,
                    'modality': models.AFQMap.fMRI_BOLD,
                    'map_type': map_type,
                    'analysis_level': models.BaseAFQMap.M,
                    'collection': collection.pk,
                    'ignore_file_warning': True,
                    'tags': ", ".join(tags)
                }

                image_description = study_element.find("./Metadata/Element[@name='Caption']").text
                if image_description:
                    post_dict["description"] = image_description.strip()

                file_dict = {'file': SimpleUploadedFile(image_filename, image_fileobject.read())}
                form = AFQMapForm(post_dict, file_dict)
                form.is_valid()
                form.save()


# THUMBNAIL IMAGE GENERATION ###########################################################################

@shared_task
def generate_glassbrain_image(image_pk):
    from afqvault.apps.afqmaps.models import Image
    import matplotlib as mpl
    mpl.rcParams['savefig.format'] = 'jpg'
    my_dpi = 50
    fig = plt.figure(figsize=(330.0 / my_dpi, 130.0 / my_dpi), dpi=my_dpi)

    img = Image.objects.get(pk=image_pk)
    f = BytesIO()
    try:
        glass_brain = plot_glass_brain(img.file.path, figure=fig)
        glass_brain.savefig(f, dpi=my_dpi)
    except:
        # Glass brains that do not produce will be given dummy image
        this_path = os.path.abspath(os.path.dirname(__file__))
        f = open(os.path.abspath(os.path.join(this_path,
                                              "static", "images", "glass_brain_empty.jpg")))
        raise
    finally:
        plt.close('all')
        f.seek(0)
        content_file = ContentFile(f.read())
        img.thumbnail.save("glass_brain_%s.jpg" % img.pk, content_file)
        img.save()

# HELPER FUNCTIONS ####################################################################################


"""Return list of Images sorted by the primary key"""


def get_images_by_ordered_id(pk1, pk2):
    from afqvault.apps.afqmaps.models import Image
    image1 = get_object_or_404(Image, pk=pk1)
    image2 = get_object_or_404(Image, pk=pk2)
    return sorted([image1, image2], key=lambda x: x.pk)
