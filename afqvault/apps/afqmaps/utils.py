import errno
import os
import pickle
import random
import string
import tempfile
import urllib2
from datetime import datetime, date

import pandas as pd
import numpy as np
import pytz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from lxml import etree

from afqvault.apps.afqmaps.models import Collection, AFQMap, Comparison, \
    BaseAFQMap


# see CollectionRedirectMiddleware
class HttpRedirectException(Exception):
    pass


def split_filename(fname):
    """Split a filename into parts: path, base filename and extension.

    Parameters
    ----------
    fname : str
        file or path name

    Returns
    -------
    pth : str
        base path from fname
    fname : str
        filename from fname, without extension
    ext : str
        file extension from fname

    Examples
    --------
    >>> from nipype.utils.filemanip import split_filename
    >>> pth, fname, ext = split_filename('/home/data/subject.nii.gz')
    >>> pth
    '/home/data'

    >>> fname
    'subject'

    >>> ext
    '.nii.gz'

    """
    special_extensions = [".nii.gz", ".tar.gz"]

    if fname and fname.endswith(os.path.sep):
        fname = fname[:-1]

    pth, fname = os.path.split(fname)

    ext = None
    for special_ext in special_extensions:
        ext_len = len(special_ext)
        if (len(fname) > ext_len) and \
                (fname[-ext_len:].lower() == special_ext.lower()):
            ext = fname[-ext_len:]
            fname = fname[:-ext_len]
            break
    if not ext:
        fname, ext = os.path.splitext(fname)

    return pth, fname, ext


def generate_url_token(length=8):
    chars = string.ascii_uppercase
    token = ''.join(random.choice(chars) for v in range(length))
    if Collection.objects.filter(private_token=token).exists():
        return generate_url_token()
    else:
        return token


def get_paper_properties(doi):
    xmlurl = 'http://doi.crossref.org/servlet/query'
    xmlpath = xmlurl + '?pid=k.j.gorgolewski@sms.ed.ac.uk&format=unixref&id=' + \
        urllib2.quote(doi)
    print xmlpath
    xml_str = urllib2.urlopen(xmlpath).read()
    doc = etree.fromstring(xml_str)
    if len(doc.getchildren()) == 0 or len(doc.findall('.//crossref/error')) > 0:
        raise Exception("DOI %s was not found" % doi)
    journal_name = doc.findall(
        ".//journal/journal_metadata/full_title")[0].text
    title = doc.findall('.//title')[0].text
    authors = [author.findall('given_name')[0].text + " " + author.findall('surname')[0].text
               for author in doc.findall('.//contributors/person_name')]
    if len(authors) > 1:
        authors = ", ".join(authors[:-1]) + " and " + authors[-1]
    else:
        authors = authors[0]
    url = doc.findall('.//doi_data/resource')[0].text
    date_node = doc.findall('.//publication_date')[0]
    if len(date_node.findall('day')) > 0:
        publication_date = date(int(date_node.findall('year')[0].text),
                                int(date_node.findall('month')[0].text),
                                int(date_node.findall('day')[0].text))
    elif len(date_node.findall('month')) > 0:
        publication_date = date(int(date_node.findall('year')[0].text),
                                int(date_node.findall('month')[0].text),
                                1)
    else:
        publication_date = date(int(date_node.findall('year')[0].text),
                                1,
                                1)
    return title, authors, url, publication_date, journal_name


def get_file_ctime(fpath):
    return datetime.fromtimestamp(os.path.getctime(fpath), tz=pytz.utc)


def splitext_nii_gz(fname):
    head, ext = os.path.splitext(fname)
    if ext.lower() == ".gz":
        _, ext2 = os.path.splitext(fname[:-3])
        ext = ext2 + ext
    return head, ext


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def send_email_notification(notif_type, subject, users, tpl_context=None):
    email_from = 'AFQVault <do_not_reply@afqvault.org>'
    plain_tpl = os.path.join('email', '%s.txt' % notif_type)
    html_tpl = os.path.join('email', '%s.html' % notif_type)

    for user in users:
        context = dict(tpl_context.items() + [('username', user.username)])
        dest = user.email
        text_content = render_to_string(plain_tpl, context)
        html_content = render_to_string(html_tpl, context)
        msg = EmailMultiAlternatives(subject, text_content, email_from, [dest])
        msg.attach_alternative(html_content, "text/html")
        msg.send()


def detect_4D(nii):
    shape = nii.shape
    return (len(shape) == 4 and shape[3] > 1 and shape[3] < 20) or (len(shape) == 5 and shape[3] == 1)


def memory_uploadfile(new_file, fname, old_file):
    cfile = ContentFile(open(new_file).read())
    content_type = getattr(old_file, 'content_type',
                           False) or 'application/x-gzip',
    charset = getattr(old_file, 'charset', False) or None

    return InMemoryUploadedFile(cfile, "file", fname,
                                content_type, cfile.size, charset)


# Atomic save for a transform pickle file - save to tmp directory and rename
def save_pickle_atomically(pkl_data, filename, directory=None):

    # Give option to save to specific (not /tmp) directory
    if directory is None:
        tmp_file = tempfile.mktemp()
    else:
        tmp_file = tempfile.mktemp(dir=directory)

    filey = open(tmp_file, 'wb')
    # We don't want pickle to close the file
    pickle_text = pickle.dumps(pkl_data)
    filey.writelines(pickle_text)
    # make sure that all data is on disk
    filey.flush()
    os.fsync(filey.fileno())
    filey.close()
    os.rename(tmp_file, filename)


def get_traceback():
    import traceback
    return traceback.format_exc() if settings.DEBUG else ''


def get_server_url(request):
    if request.META.get('HTTP_ORIGIN'):
        return request.META['HTTP_ORIGIN']
    urlpref = 'https://' if request.is_secure() else 'http://'
    return '{0}{1}'.format(urlpref, request.META['HTTP_HOST'])


# Returns string in format image: collection [map_type] to be within
# total_length
def format_image_collection_names(image_name, collection_name, total_length, map_type=None):
    # 3/5 total length should be collection, 2/5 image
    collection_length = int(np.floor(.60 * total_length))
    image_length = int(np.floor(total_length - collection_length))
    if len(image_name) > image_length:
        image_name = "%s..." % image_name[0:image_length]
    if len(collection_name) > collection_length:
        collection_name = "%s..." % collection_name[0:collection_length]
    if map_type is None:
        return "%s : %s" % (image_name, collection_name)
    else:
        return "%s : %s [%s]" % (image_name, collection_name, map_type)

# checks if map is thresholded


def is_thresholded(nii_obj, thr=0.85):
    data = nii_obj.get_data()
    zero_mask = (data == 0)
    nan_mask = (np.isnan(data))
    missing_mask = zero_mask | nan_mask
    ratio_bad = float(missing_mask.sum()) / float(missing_mask.size)
    if ratio_bad > thr:
        return (True, ratio_bad)
    else:
        return (False, ratio_bad)


# checks if map is a parcellation or ROI/mask
def infer_map_type(nii_obj):
    data = nii_obj.get_data()
    zero_mask = (data == 0)
    nan_mask = (np.isnan(data))
    missing_mask = zero_mask | nan_mask
    unique_values = np.unique(data[np.logical_not(missing_mask)])
    if len(unique_values) == 1:
        map_type = BaseAFQMap.R
    elif len(unique_values) > 1200:
        map_type = BaseAFQMap.OTHER
    else:
        map_type = BaseAFQMap.Pa
        for val in unique_values:
            if not(isinstance(val, np.integer) or (isinstance(val, np.floating) and float(val).is_integer())):
                map_type = BaseAFQMap.OTHER
                break
            if (data == val).sum() == 1:
                map_type = BaseAFQMap.OTHER
                break
    return map_type


# QUERY FUNCTIONS --------------------------------------------------------


def is_search_compatible(pk):
    from afqvault.apps.afqmaps.models import Image
    try:
        img = Image.objects.get(pk=pk)
    except ObjectDoesNotExist:
        return False

    if img.polymorphic_ctype.model in ['image', 'atlas'] or \
       img.is_thresholded or \
       img.analysis_level == 'S' or \
       img.map_type in ['R', 'Pa', 'A'] or img.collection.private:
        return False
    else:
        return True


def get_images_to_compare_with(pk1, for_generation=False):
    from afqvault.apps.afqmaps.models import AFQMap, Image

    # if the map in question is invalid do not generate any comparisons
    if not is_search_compatible(pk1):
        return []

    img = Image.objects.get(pk=pk1)
    image_pks = []
    for cls in [AFQMap]:
        qs = cls.objects.filter(
            collection__private=False, is_thresholded=False)
        if not (for_generation and img.collection.DOI is not None):
            qs = qs.exclude(collection__DOI__isnull=True)
        qs = qs.exclude(collection=img.collection)
        qs = qs.exclude(pk=pk1).exclude(analysis_level='S').exclude(
            map_type='R').exclude(map_type='Pa')
        image_pks += list(qs.values_list('pk', flat=True))
    return image_pks

# Returns number of total comparisons, with public, not thresholded maps


def count_existing_comparisons(pk1):
    return get_existing_comparisons(pk1).count()

# Returns number of total comparisons possible


def count_possible_comparisons(pk1):
    # Comparisons possible for one pk is the number of other pks
    count_statistic_maps = AFQMap.objects.filter(is_thresholded=False, collection__private=False).exclude(
        pk=pk1).exclude(analysis_level='S').count()
    return count_statistic_maps

# Returns image comparisons still processing for a given pk


def count_processing_comparisons(pk1):
    return count_possible_comparisons(pk1) - count_existing_comparisons(pk1)


# Returns existing comparisons for specific pk, or entire database
def get_existing_comparisons(pk1):
    possible_images_to_compare_with_pks = get_images_to_compare_with(
        pk1) + [pk1]
    comparisons = Comparison.objects.filter(
        Q(image1__pk=pk1) | Q(image2__pk=pk1))
    comparisons = comparisons.filter(image1__id__in=possible_images_to_compare_with_pks,
                                     image2__id__in=possible_images_to_compare_with_pks)
    comparisons = comparisons.exclude(image1__pk=pk1, image2__pk=pk1)
    return comparisons

# Returns existing comparisons for specific pk in pd format for


def get_similar_images(pk, max_results=100):
    comparisons = get_existing_comparisons(pk).extra(select={"abs_score": "abs(similarity_score)"}).order_by(
        "-abs_score")[0:max_results]  # "-" indicates descending

    comparisons_pd = pd.DataFrame({'image_id': [],
                                   'score': [],
                                   'png_img_path': [],
                                   'tag': [],
                                   'name': [],
                                   'collection_name': []
                                   })

    for comp in comparisons:
        # pick the image we are comparing with
        image = [image for image in [
            comp.image1, comp.image2] if image.id != pk][0]
        if hasattr(image, "map_type") and image.thumbnail:
            df = pd.DataFrame({'image_id': [image.pk],
                               'score': [comp.similarity_score],
                               'png_img_path': [image.get_thumbnail_url()],
                               'tag': [[str(image.map_type)]],
                               'name': [image.name],
                               'collection_name': [image.collection.name]
                               })
        comparisons_pd = comparisons_pd.append(df, ignore_index=True)

    return comparisons_pd
