import csv
import functools
import gzip
import json
import numpy as np
import os
import re
import shutil
import tarfile
import tempfile
import traceback
import urllib
import zipfile
import zipstream
from collections import OrderedDict
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db.models import Q
from django.db.models.aggregates import Count
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response, render, redirect
from django.template.context import RequestContext
from django.utils.encoding import filepath_to_uri
from django.views.decorators.csrf import csrf_exempt
from django_datatables_view.base_datatable_view import BaseDatatableView
from fnmatch import fnmatch
from guardian.shortcuts import get_objects_for_user
from pybraincompare.compare.scatterplot import scatterplot_compare_vector
from rest_framework.renderers import JSONRenderer
from sendfile import sendfile
from sklearn.externals import joblib
from xml.dom import minidom

import afqvault
from afqvault import settings
from afqvault.apps.afqmaps.ahba import calculate_gene_expression_similarity
from afqvault.apps.afqmaps.forms import CollectionForm, UploadFileForm, SimplifiedAFQMapForm,NeuropowerAFQMapForm,\
    AFQMapForm, EditAFQMapForm, OwnerCollectionForm, EditAtlasForm, AtlasForm, \
    Form, AddAFQMapForm
from afqvault.apps.afqmaps.models import Collection, Image, Atlas, AFQMap, \
    BaseAFQMap
from afqvault.apps.afqmaps.utils import split_filename, \
    generate_url_token, HttpRedirectException, get_paper_properties, \
    get_file_ctime, splitext_nii_gz, mkdir_p, \
    send_email_notification, get_server_url, \
    format_image_collection_names, is_search_compatible, \
    get_similar_images
from afqvault.apps.afqmaps.voxel_query_functions import *
from . import image_metadata


def owner_or_contrib(request,collection):
    '''owner_or_contrib determines if user is an owner or contributor to a collection
    :param collection: afqmaps.models.Collection
    '''
    return request.user.has_perm('afqmaps.change_collection', collection) or request.user.is_superuser


def get_collection(cid,request,mode=None):
    '''get_collection returns collection object based on a primary key (cid)
    :param cid: afqmaps.models.Collection.pk the primary key of the collection
    '''
    keyargs = {'pk':cid}
    private_url = re.match(r'^[A-Z]{8}$',cid)
    if private_url is not None:
        keyargs = {'private_token':cid}
    try:
        collection = Collection.objects.get(**keyargs)
        if private_url is None and collection.private:
            if owner_or_contrib(request,collection):
                if mode in ['file','api']:
                    raise PermissionDenied()
                else:
                    raise HttpRedirectException(collection.get_absolute_url())
            else:
                raise PermissionDenied()
    except Collection.DoesNotExist:
        raise Http404
    else:
        return collection


def get_image(pk,collection_cid,request,mode=None):
    '''get_image returns image object from a collection based on a primary key (pk)
    :param pk: afqmaps.models.Image.pk the primary key of the image
    :param collection_cid: the primary key of the image collection
    '''
    image = get_object_or_404(Image, pk=pk)
    if image.collection.private and image.collection.private_token != collection_cid:
        if owner_or_contrib(request,image.collection):
            if mode == 'api':
                raise PermissionDenied()
            else:
                raise HttpRedirectException(image.get_absolute_url())
        else:
            raise PermissionDenied()
    else:
        return image

@login_required
def edit_collection(request, cid=None):
    '''edit_collection is a view to edit a collection, meaning showing the edit form for an existing collection, creating a new collection, or passing POST data to update an existing collection
    :param cid: afqmaps.models.Collection.pk the primary key of the collection. If none, will generate form to make a new collection.
    '''
    page_header = "Add new collection"
    if cid:
        collection = get_collection(cid, request)
        edit_permission = request.user.has_perm('afqmaps.change_collection', collection)
        is_owner = request.user.has_perm('afqmaps.delete_collection', collection)
        page_header = 'Edit collection'
        if not edit_permission:
            return HttpResponseForbidden()
    else:
        is_owner = True
        collection = Collection(owner=request.user)
    if request.method == "POST":
        if is_owner:
            form = OwnerCollectionForm(request.POST, request.FILES, instance=collection)
        else:
            form = CollectionForm(request.POST, request.FILES, instance=collection)
        if form.is_valid():
            previous_contribs = set()
            if form.instance.pk is not None:
                previous_contribs = set(form.instance.contributors.all())
            collection = form.save(commit=False)
            if collection.private and collection.private_token is None:
                collection.private_token = generate_url_token()
            collection.save()

            if is_owner:
                form.save_m2m()  # save contributors
                current_contribs = set(collection.contributors.all())
                new_contribs = list(current_contribs.difference(previous_contribs))
                context = {
                    'owner': collection.owner.username,
                    'collection': collection.name,
                    'url': get_server_url(request) + collection.get_absolute_url(),
                }
                subj = '%s has added you to a AFQVault collection' % context['owner']
                send_email_notification('new_contributor', subj, new_contribs, context)

            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        if is_owner:
            form = OwnerCollectionForm(instance=collection)
        else:
            form = CollectionForm(instance=collection)

    context = {"form": form, "page_header": page_header, "is_owner": is_owner}
    return render(request, "afqmaps/edit_collection.html.haml", context)


def choice_datasources(model):
    statmap_field_obj = functools.partial(image_metadata.get_field_by_name,model)
    pick_second_item = functools.partial(map, lambda x: x[1])
    fixed_fields = list(model.get_fixed_fields())
    field_choices = ((f, statmap_field_obj(f).choices) for f in fixed_fields)
    fields_with_choices = (t for t in field_choices if t[1])
    return dict((field_name, pick_second_item(choices))
                for field_name, choices in fields_with_choices)


def get_field_datasources():
    ds = choice_datasources(AFQMap)
    return ds

@csrf_exempt
@login_required
def edit_metadata(request, collection_cid):
    collection = get_collection(collection_cid, request)

    if not owner_or_contrib(request, collection):
        return HttpResponseForbidden()

    if not collection.is_statisticmap_set:
        return HttpResponseForbidden('Editing image metadata of collections '
                                     'that include not only statistical '
                                     'maps is forbidden.')

    if request.method == "POST":
        return JSONResponse(
            **image_metadata.handle_post_metadata(
                request, collection, 'Images metadata have been saved.'))

    collection_images = collection.basecollectionitem_set.instance_of(Image).order_by('pk')
    data_headers = image_metadata.get_data_headers(collection_images)
    metadata = image_metadata.get_images_metadata(collection_images)
    datasources = get_field_datasources()

    return render(request, "afqmaps/edit_metadata.html", {
        'collection': collection,
        'datasources': json.dumps(datasources),
        'data_headers': json.dumps(data_headers),
        'metadata': json.dumps(metadata)})


@login_required
def export_images_filenames(request, collection_cid):
    collection = get_collection(collection_cid, request)
    images_filenames = image_metadata.get_images_filenames(collection)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; ' \
                                      'filename="collection_%s.csv"' % (
                                          collection.id)

    writer = csv.writer(response)
    writer.writerows([['Filename']] + [[name] for name in images_filenames])

    return response


def view_image(request, pk, collection_cid=None):
    '''view_image returns main view to see an image and associated meta data. If the image is in a collection with a DOI and has a generated thumbnail, it is a contender for image comparison, and a find similar button is exposed.
    :param pk: afqmaps.models.Image.pk the primary key of the image
    :param collection_cid: afqmaps.models.Collection.pk the primary key of the collection. Default None
    '''
    image = get_image(pk,collection_cid,request)
    user_owns_image = owner_or_contrib(request,image.collection)
    api_cid = pk

    comparison_is_possible = is_search_compatible(pk) and image.thumbnail

    if image.collection.private:
        api_cid = '%s-%s' % (image.collection.private_token,pk)
    context = {
        'image': image,
        'user': image.collection.owner,
        'user_owns_image': user_owns_image,
        'api_cid': api_cid,
        'comparison_is_possible': comparison_is_possible
    }

    if isinstance(image, Atlas):
        template = 'afqmaps/atlas_details.html.haml'
    else:
        if np.isnan(image.perc_bad_voxels) or np.isnan(image.perc_voxels_outside):
            context['warning'] = "Warning: This map seems to be empty!"
        elif not image.is_valid:
            context['warning'] = "Warning: This map is missing some mandatory metadata!"
            if user_owns_image:
                context['warning'] += " Please <a href='edit'>edit image details</a> to provide the missing information."
        elif image.not_mni:
            context['warning'] = "Warning: This map seems not to be in the MNI space (%.4g%% of meaningful voxels are outside of the brain). "%image.perc_voxels_outside
            context['warning'] += "Please transform the map to MNI space. "
        elif image.is_thresholded:
            context['warning'] = "Warning: This map seems to be thresholded, sparse or acquired with limited field of view (%.4g%% of voxels are zeros). "%image.perc_bad_voxels
            context['warning'] += "Some of the AFQVault functions such as decoding might not work properly. "
            context['warning'] += "Please use unthresholded maps whenever possible."

        template = 'afqmaps/statisticmap_details.html.haml'
    return render(request, template, context)


def view_collection(request, cid):
    '''view_collection returns main view to see an entire collection of images, meaning a viewer and list of images to load into it.
    :param cid: afqmaps.models.Collection.pk the primary key of the collection
    '''
    collection = get_collection(cid,request)
    edit_permission = request.user.has_perm('afqmaps.change_collection', collection)
    delete_permission = request.user.has_perm('afqmaps.delete_collection', collection)
    is_empty = not collection.basecollectionitem_set.exists()
    context = {'collection': collection,
            'is_empty': is_empty,
            'user': request.user,
            'delete_permission': delete_permission,
            'edit_permission': edit_permission,
            'cid':cid}

    if not all(collection.basecollectionitem_set.instance_of(AFQMap).values_list('is_valid', flat=True)):
        msg = "Some of the images in this collection are missing crucial metadata."
        if owner_or_contrib(request,collection):
            msg += " Please add the missing information by <a href='editmetadata'>editing images metadata</a>."
        context["messages"] = [msg]

    if not is_empty:
        context["first_image"] = collection.basecollectionitem_set.order_by("pk")[0]

    if owner_or_contrib(request,collection):
        form = UploadFileForm()
        c = RequestContext(request)
        c.update(context)
        return render_to_response('afqmaps/collection_details.html', {'form': form}, c)
    else:
        return render(request, 'afqmaps/collection_details.html', context)


@login_required
def delete_collection(request, cid):
    collection = get_collection(cid,request)
    if not request.user.has_perm('afqmaps.delete_collection', collection):
        return HttpResponseForbidden()
    collection.delete()
    return redirect('my_collections')


@login_required
def edit_image(request, pk):
    image = get_object_or_404(Image,pk=pk)
    if isinstance(image, AFQMap):
        form = EditAFQMapForm
    elif isinstance(image, Atlas):
        form = EditAtlasForm
    else:
        raise Exception("unsupported image type")
    if not owner_or_contrib(request,image.collection):
        return HttpResponseForbidden()
    if request.method == "POST":
        form = form(request.POST, request.FILES, instance=image, user=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = form(instance=image, user=request.user)

    context = {"form": form}
    return render(request, "afqmaps/edit_image.html", context)

def add_image_redirect(request,formclass,template_path,redirect_url,is_private):
    temp_collection_name = "%s's temporary collection" % request.user.username
    #this is a hack we need to make sure this collection can be only
    #owned by the same user
    try:
        temp_collection = Collection.objects.get(name=temp_collection_name)
    except Collection.DoesNotExist:
        priv_token = generate_url_token()
        temp_collection = Collection(name=temp_collection_name,
                                     owner=request.user,
                                     private=is_private,
                                     private_token=priv_token)
        temp_collection.save()
    image = AFQMap(collection=temp_collection)
    if request.method == "POST":
        form = formclass(request.POST, request.FILES, instance=image, user=request.user)
        if form.is_valid():
            image = form.save()
            redirect = redirect_url % {
                'private_token': temp_collection.private_token,
                'image_id': image.id}
            return HttpResponseRedirect(redirect)
    else:
        form = formclass(user=request.user, instance=image)
    context = {"form": form}
    return render(request,template_path , context)

@login_required
def add_image_for_neurosynth(request):
    redirect_url = "http://neurosynth.org/decode/?afqvault=%(private_token)s-%(image_id)s"
    template_path = "afqmaps/add_image_for_neurosynth.html"
    return add_image_redirect(request,SimplifiedAFQMapForm,template_path,redirect_url,False)

@login_required
def add_image_for_neuropower(request):
    redirect_url = "http://neuropowertools.org/neuropower/neuropowerinput/?afqvault=%(private_token)s-%(image_id)s"
    template_path = "afqmaps/add_image_for_neuropower.html"
    return add_image_redirect(request,NeuropowerAFQMapForm,template_path,redirect_url,True)

@login_required
def add_image(request, collection_cid):
    collection = get_collection(collection_cid,request)
    if not owner_or_contrib(request,collection):
        return HttpResponseForbidden()
    image = AFQMap(collection=collection)
    if request.method == "POST":
        form = AddAFQMapForm(request.POST, request.FILES, instance=image)
        if form.is_valid():
            image = form.save()
            return HttpResponseRedirect(image.get_absolute_url())
    else:
        form = AddAFQMapForm(instance=image)

    context = {"form": form}
    return render(request, "afqmaps/add_image.html", context)


@login_required
def upload_folder(request, collection_cid):
    collection = get_collection(collection_cid,request)
    files = []
    if request.method == 'POST':
        print request.POST
        print request.FILES
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            tmp_directory = tempfile.mkdtemp()
            print tmp_directory
            try:
                # Save archive (.zip or .tar.gz) to disk
                if "file" in request.FILES:
                    archive_name = request.FILES['file'].name
                    _, archive_ext = os.path.splitext(archive_name)
                    if archive_ext == '.zip':
                        compressed = zipfile.ZipFile(request.FILES['file'])
                    elif archive_ext == '.gz':
                        django_file = request.FILES['file']
                        django_file.open()
                        compressed = tarfile.TarFile(fileobj=gzip.GzipFile(fileobj=django_file.file, mode='r'), mode='r')
                    else:
                        raise Exception("Unsupported archive type %s."%archive_name)
                    compressed.extractall(path=tmp_directory)

                elif "file_input[]" in request.FILES:

                    for f, path in zip(request.FILES.getlist(
                                       "file_input[]"), request.POST.getlist("paths[]")):
                        new_path, _ = os.path.split(os.path.join(tmp_directory, path))
                        mkdir_p(new_path)
                        filename = os.path.join(new_path,f.name)
                        tmp_file = open(filename, 'w')
                        tmp_file.write(f.read())
                        tmp_file.close()
                else:
                    raise Exception("Unable to find uploaded files.")

                atlases = {}
                for root, subdirs, filenames in os.walk(tmp_directory):

                    filenames = [f for f in filenames if not f[0] == '.']
                    for fname in sorted(filenames):
                        name, ext = splitext_nii_gz(fname)
                        nii_path = os.path.join(root, fname)

                        if ext == '.xml':
                            dom = minidom.parse(os.path.join(root, fname))
                            for atlas in dom.getElementsByTagName("imagefile"):
                                path, base = os.path.split(atlas.lastChild.nodeValue)
                                nifti_name = os.path.join(path, base)
                                if nifti_name.startswith("/"):
                                    nifti_name = nifti_name[1:]
                                atlases[str(os.path.join(root,
                                            nifti_name))] = os.path.join(root, fname)
                        if ext in Image.allowed_extensions:
                            files.append((fname, nii_path))

                for label, fpath in files:
                    path, name, ext = split_filename(fpath)
                    spaced_name = name.replace('_',' ').replace('-', ' ')
                    f = ContentFile(open(fpath).read(), name=dname)

                    collection = get_collection(collection_cid, request)

                    if os.path.join(path, name) in atlases:
                        new_image = Atlas(name=spaced_name,
                                          description=raw_hdr['descrip'], collection=collection)

                        new_image.label_description_file = ContentFile(
                                    open(atlases[os.path.join(path,name)]).read(),
                                                                    name=name + ".xml")
                    else:
                        new_image = AFQMap(name=spaced_name, is_valid=False,
                                description=raw_hdr['descrip'] or label, collection=collection)
                        new_image.map_type = map_type

                    new_image.file = f
                    new_image.save()

            except:
                error = traceback.format_exc().splitlines()[-1]
                msg = "An error occurred with this upload: {}".format(error)
                messages.warning(request, msg)
                return HttpResponseRedirect(collection.get_absolute_url())
            finally:
                shutil.rmtree(tmp_directory)
            if not files:
                messages.warning(request, "No files (%s) found in the upload." % ','.join(Image.allowed_extensions))
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        form = UploadFileForm()
    return render_to_response("afqmaps/upload_folder.html",
                              {'form': form},  RequestContext(request))


@login_required
def delete_image(request, pk):
    image = get_object_or_404(Image,pk=pk)
    cid = image.collection.pk
    if not request.user.has_perm("afqmaps.delete_basecollectionitem", image):
        return HttpResponseForbidden()
    image.delete()
    return redirect('collection_details', cid=cid)



def view_images_by_tag(request, tag):
    if request.user.is_authenticated():
        images = Image.objects.filter(tags__name__in=[tag]).filter(
                                        Q(collection__private=False) |
                                        Q(collection__owner=request.user))
    else:
        images = Image.objects.filter(tags__name__in=[tag]).filter(
                                        collection__private=False)
    context = {'images': images, 'tag': tag}
    return render(request, 'afqmaps/images_by_tag.html.haml', context)

def serve_image(request, collection_cid, img_name):
    collection = get_collection(collection_cid,request,mode='file')
    path = os.path.join(settings.PRIVATE_MEDIA_ROOT,'images',str(collection.id),img_name)
    return sendfile(request, path, encoding="utf-8")

def stats_view(request):
    collections_by_journals = {}
    for collection in Collection.objects.filter(
                                private=False).exclude(Q(DOI__isnull=True) | Q(DOI__exact='')):
        if not collection.journal_name:
            _,_,_,_, collection.journal_name = get_paper_properties(collection.DOI)
            collection.save()
        if collection.journal_name not in collections_by_journals.keys():
            collections_by_journals[collection.journal_name] = 1
        else:
            collections_by_journals[collection.journal_name] += 1
    collections_by_journals = OrderedDict(sorted(collections_by_journals.items(
                                                ), key=lambda t: t[1], reverse=True))

    non_empty_collections_count = Collection.objects.annotate(num_submissions=Count('basecollectionitem')).filter(num_submissions__gt = 0).count()
    public_collections_count = Collection.objects.filter(private=False).annotate(num_submissions=Count('basecollectionitem')).filter(num_submissions__gt = 0).count()
    public_collections_with_DOIs_count = Collection.objects.filter(private=False).exclude(Q(DOI__isnull=True) | Q(DOI__exact='')).annotate(num_submissions=Count('basecollectionitem')).filter(num_submissions__gt = 0).count()
    context = {'collections_by_journals': collections_by_journals,
               'non_empty_collections_count': non_empty_collections_count,
               'public_collections_count': public_collections_count,
               'public_collections_with_DOIs_count': public_collections_with_DOIs_count}
    return render(request, 'afqmaps/stats.html.haml', context)


def papaya_js_embed(request, pk, iframe=None):
    tpl = 'papaya_embed.tpl.js'
    mimetype = "text/javascript"
    if iframe is not None:
        tpl = 'papaya_frame.html.haml'
        mimetype = "text/html"
    image = get_image(pk,None,request)
    if image.collection.private:
        return HttpResponseForbidden()
    context = {'image': image, 'request':request}
    return render_to_response('afqmaps/%s' % tpl,
                              context, content_type=mimetype)


@csrf_exempt
def atlas_query_region(request):
    # this query is significantly faster (from 2-4 seconds to <1 second) if the synonyms don't need to be queried
    # i was previously in contact with NIF and it seems like it wouldn't be too hard to download all the synonym data
    search = request.GET.get('region','')
    atlas = request.GET.get('atlas','').replace('\'', '')
    collection = name=request.GET.get('collection','')
    afqvault_root = os.path.dirname(os.path.dirname(os.path.realpath(afqvault.__file__)))
    try:
        collection_object = Collection.objects.filter(name=collection)[0]
    except IndexError:
        return JSONResponse('error: could not find collection: %s' % collection, status=400)
    try:
        atlas_object = Atlas.objects.filter(name=atlas, collection=collection_object)[0]
        atlas_image = atlas_object.file
        atlas_xml = atlas_object.label_description_file
    except IndexError:
        return JSONResponse('could not find %s' % atlas, status=400)
    if request.method == 'GET':
        atlas_xml.open()
        root = ET.fromstring(atlas_xml.read())
        atlas_xml.close()
        atlasRegions = [x.text.lower() for x in root.find('data').findall('label')]
        if search in atlasRegions:
            searchList = [search]
        else:
            synonymsDict = {}
            with open(os.path.join(afqvault_root, 'afqvault/apps/afqmaps/NIFgraph.pkl'),'rb') as input:
                graph = joblib.load(input)
            for atlasRegion in atlasRegions:
                synonymsDict[atlasRegion] = getSynonyms(atlasRegion)
            try:
                searchList = toAtlas(search, graph, atlasRegions, synonymsDict)
            except ValueError:
                return JSONResponse('error: region not in atlas or ontology', status=400)
            if searchList == 'none':
                return JSONResponse('error: could not map specified region to region in specified atlas', status=400)
        try:
            data = {'voxels':getAtlasVoxels(searchList, atlas_image, atlas_xml)}
        except ValueError:
            return JSONResponse('error: region not in atlas', status=400)

        return JSONResponse(data)


@csrf_exempt
def atlas_query_voxel(request):
    X = request.GET.get('x','')
    Y = request.GET.get('y','')
    Z = request.GET.get('z','')
    collection = name = request.GET.get('collection','')
    atlas = request.GET.get('atlas','').replace('\'', '')
    try:
        collection_object = Collection.objects.filter(name=collection)[0]
    except IndexError:
        return JSONResponse('error: could not find collection: %s' % collection, status=400)
    try:
        atlas_object = Atlas.objects.filter(name=atlas, collection=collection_object)[0]
        atlas_image = atlas_object.file
        atlas_xml = atlas_object.label_description_file
    except IndexError:
        return JSONResponse('error: could not find atlas: %s' % atlas, status=400)
    try:
        data = voxelToRegion(X,Y,Z,atlas_image, atlas_xml)
    except IndexError:
        return JSONResponse('error: one or more coordinates are out of range', status=400)
    return JSONResponse(data)


# Compare Two Images
def compare_images(request,pk1,pk2):
    import numpy as np
    image1 = get_image(pk1,None,request)
    image2 = get_image(pk2,None,request)
    images = [image1,image2]

    # Get image: collection: [map_type] names no longer than ~125 characters
    image1_custom_name = format_image_collection_names(image_name=image1.name,
                                                       collection_name=image1.collection.name,
                                                       map_type=image1.map_type,total_length=125)
    image2_custom_name = format_image_collection_names(image_name=image2.name,
                                                       collection_name=image2.collection.name,
                                                       map_type=image2.map_type,total_length=125)

    image_names = [image1_custom_name,image2_custom_name]

    # Create custom links for the visualization
    custom = {
            "IMAGE_1_LINK":"/images/%s" % (image1.pk),
            "IMAGE_2_LINK":"/images/%s" % (image2.pk)
    }

    # Load image vectors from npy files
    image_vector1 = np.load(image1.reduced_representation.file)
    image_vector2 = np.load(image2.reduced_representation.file)

    # Load atlas pickle, containing vectors of atlas labels, colors, and values for same voxel dimension (4mm)
    this_path = os.path.abspath(os.path.dirname(__file__))
    atlas_pkl_path = os.path.join(this_path, 'static/atlas/atlas_mni_4mm.pkl')
    atlas = joblib.load(atlas_pkl_path)

    # Load the atlas svg, so we don't need to dynamically generate it
    atlas_svg = os.path.join(this_path, 'static/atlas/atlas_mni_2mm_svg.pkl')
    atlas_svg = joblib.load(atlas_svg)

    # Generate html for similarity search, do not specify atlas
    html_snippet, _ = scatterplot_compare_vector(image_vector1=image_vector1,
                                                                 image_vector2=image_vector2,
                                                                 image_names=image_names,
                                                                 atlas_vector=atlas["atlas_vector"],
                                                                 atlas_labels=atlas["atlas_labels"],
                                                                 atlas_colors=atlas["atlas_colors"],
                                                                 corr_type="pearson",
                                                                 subsample_every=10, # subsample every 10th voxel
                                                                 custom=custom,
                                                                 remove_scripts="D3_MIN_JS",
                                                                 width=1000)

    # Add atlas svg to the image, and prepare html for rendering
    html = [h.replace("[coronal]",atlas_svg) for h in html_snippet]
    html = [h.strip("\n").replace("[axial]","").replace("[sagittal]","") for h in html]
    context = {'html': html}

    # Determine if either image is thresholded
    threshold_status = np.array([image_names[i] for i in range(0,2) if images[i].is_thresholded])
    if len(threshold_status) > 0:
        warnings = list()
        for i in range(0,len(image_names)):
            warnings.append('Warning: Thresholded image: %s (%.4g%% of voxels are zeros),' %(image_names[i],images[i].perc_bad_voxels))
        context["warnings"] = warnings

    return render(request, 'afqmaps/compare_images.html', context)


# Return search interface for one image vs rest
def find_similar(request, pk):
    image1 = get_image(pk, None, request)
    pk = int(pk)
    max_results = 10

    # Search only enabled if the image is not thresholded
    if image1.is_thresholded:
        error_message = "Image comparison is not enabled for thresholded images."
        context = {'error_message': error_message}
        return render(request, 'afqmaps/error_message.html', context)

    image_title = format_image_collection_names(image_name=image1.name,
                                                    collection_name=image1.collection.name,
                                                    map_type=image1.map_type, total_length=50)
    # Here is the query image
    query_png = image1.thumbnail.url

    context = {
        'image': image1,
        'image_title': image_title,
        'query_png': query_png
    }
    template = 'afqmaps/compare_search.html.haml'
    return render(request, template, context)


def find_similar_json(request, pk, collection_cid=None):

    limit = 500 # maximum number of Comparisons allowed to retrieve
    max_results = int(request.GET.get('q', '100'))
    if max_results > limit:
        max_results = limit

    image1 = get_image(pk, None, request)
    pk = int(pk)

    # Search only enabled if the image is not thresholded
    if image1.is_thresholded:
        return JSONResponse('error: Image comparison is not enabled for thresholded images.', status=400)
    else:
        similar_images = get_similar_images(pk, max_results)

    dict = similar_images.to_dict("split")
    del dict["index"]
    return JSONResponse(dict)

def gene_expression(request, pk, collection_cid=None):
    '''view_image returns main view to see an image and associated meta data. If the image is in a collection with a DOI and has a generated thumbnail, it is a contender for image comparison, and a find similar button is exposed.
    :param pk: afqmaps.models.Image.pk the primary key of the image
    :param collection_cid: afqmaps.models.Collection.pk the primary key of the collection. Default None
    '''
    image = get_image(pk, collection_cid, request)
    if image.is_thresholded:
        raise Http404
    api_cid = pk
    if image.collection.private:
        api_cid = '%s-%s' % (image.collection.private_token,pk)
    context = {
        'image': image,
        'api_cid': api_cid,
    }
    template = 'afqmaps/gene_expression.html.haml'
    return render(request, template, context)

def gene_expression_json(request, pk, collection_cid=None):
    image = get_image(pk, collection_cid, request)
    if image.is_thresholded:
        raise Http404

    map_data = np.load(image.reduced_representation.file)
    expression_results = calculate_gene_expression_similarity(map_data)
    dict = expression_results.to_dict("split")
    del dict["index"]
    return JSONResponse(dict)

# Return search interface
def search(request,error_message=None):
    context = {'message': error_message}
    return render(request, 'afqmaps/search.html', context)


class JSONResponse(HttpResponse):
    """
    An HttpResponse that renders its content into JSON.
    """
    def __init__(self, data, **kwargs):
        content = JSONRenderer().render(data)
        kwargs['content_type'] = 'application/json'
        super(JSONResponse, self).__init__(content, **kwargs)


class ImagesInCollectionJson(BaseDatatableView):
    columns = ['file.url', 'pk', 'name', 'polymorphic_ctype.name', 'is_valid']
    order_columns = ['','pk', 'name', 'polymorphic_ctype.name', '']

    def get_initial_queryset(self):
        # return queryset used as base for futher sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        collection = get_collection(self.kwargs['cid'], self.request)
        return collection.basecollectionitem_set.all()

    def render_column(self, row, column):
        if row.polymorphic_ctype.name == "statistic map":
            type = row.get_map_type_display()
        else:
            type = row.polymorphic_ctype.name

        # We want to render user as a custom column
        if column == 'file.url':
            if isinstance(row, Image):
                return '<a class="btn btn-default viewimage" onclick="viewimage(this)" filename="%s" type="%s"><i class="fa fa-lg fa-eye"></i></a>'%(filepath_to_uri(row.file.url), type)
        elif column == 'polymorphic_ctype.name':
            return type
        elif column == 'is_valid':
            return row.is_valid
        else:
            return super(ImagesInCollectionJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get(u'search[value]', None)
        if search:
            qs = qs.filter(Q(name__icontains=search)| Q(description__icontains=search))
        return qs


    def get_initial_queryset(self):
        # Do not filter by task here, we may want other parameters
        return AFQMap.objects.filter(collection__private=False)


    def render_column(self, row, column):
        # We want to render user as a custom column
        if column == 'file.url':
            if isinstance(row, Image):
                return '<a class="btn btn-default viewimage" onclick="viewimage(this)" filename="%s" type="%s"><i class="fa fa-lg fa-eye"></i></a>'%(filepath_to_uri(row.file.url), type)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset
        # simple example:
        search = self.request.GET.get(u'search[value]', None)
        if search:
            qs = qs.filter(Q(name__icontains=search)| Q(id__icontains=search))
        return qs


class AtlasesAndParcellationsJson(BaseDatatableView):
    columns = ['file.url', 'name', 'collection.name', 'collection.authors', 'polymorphic_ctype.name']
    order_columns = ['','name', 'polymorphic_ctype.name']

    def get_initial_queryset(self):
        # return queryset used as base for futher sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        qs = Image.objects.instance_of(Atlas) | Image.objects.instance_of(AFQMap).filter(statisticmap__map_type=BaseAFQMap.Pa)
        qs = qs.filter(collection__private=False).exclude(collection__DOI__isnull=True)
        return qs


    def render_column(self, row, column):
        if row.polymorphic_ctype.name == "statistic map":
            type = row.get_map_type_display()
        else:
            type = row.polymorphic_ctype.name

        # We want to render user as a custom column
        if column == 'file.url':
            return '<a class="btn btn-default viewimage" onclick="viewimage(this)" filename="%s" type="%s"><i class="fa fa-lg fa-eye"></i></a>'%(filepath_to_uri(row.file.url), type)
        elif column == 'polymorphic_ctype.name':
            return type
        if column == 'collection.authors' and row.collection.authors:
            return row.collection.authors.split(',')[0].split(' ')[-1] + " et al."
        if column == 'collection.name':
            return "<a href='" + row.collection.get_absolute_url() + "'>" + row.collection.name + "</a>"
        else:
            return super(AtlasesAndParcellationsJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get(u'search[value]', None)
        if search:
            qs = qs.filter(Q(name__icontains=search)| Q(description__icontains=search))
        return qs

class PublicCollectionsJson(BaseDatatableView):
    columns = ['name', 'n_images', 'description', 'has_doi']
    order_columns = ['name', '', 'description', '']

    def get_initial_queryset(self):
        # return queryset used as base for futher sorting/filtering
        # these are simply objects displayed in datatable
        # You should not filter data returned here by any filter values entered by user. This is because
        # we need some base queryset to count total number of records.
        return Collection.objects.filter(~Q(name__endswith = "temporary collection"), private=False)

    def render_column(self, row, column):
        # We want to render user as a custom column
        if column == 'has_doi':
            if row.DOI:
                return "Yes"
            else:
                return ""
        elif column == 'n_images':
            return row.basecollectionitem_set.count()
        else:
            return super(PublicCollectionsJson, self).render_column(row, column)

    def filter_queryset(self, qs):
        # use parameters passed in GET request to filter queryset

        # simple example:
        search = self.request.GET.get(u'search[value]', None)
        if search:
            qs = qs.filter(Q(name__icontains=search)| Q(description__icontains=search))
        return qs

class MyCollectionsJson(PublicCollectionsJson):

    def get_initial_queryset(self):
        return get_objects_for_user(self.request.user, 'afqmaps.change_collection')


def download_collection(request, cid):
    # Files (local path) to put in the .zip
    collection = get_collection(cid, request)

    filenames = [img.file.path for img in
                 (collection.basecollectionitem_set.instance_of(Image))]

    # Folder name in ZIP archive which contains the above files
    # E.g [collection.name.zip]/collection.name/img.id.nii.gz
    zip_subdir = collection.name
    zip_filename = '%s.zip' % collection.name

    zf = zipstream.ZipFile(mode='w', compression=zipstream.ZIP_DEFLATED)

    for fpath in filenames:
        # Calculate path for file in zip
        fdir, fname = os.path.split(fpath)
        zip_path = os.path.join(zip_subdir, fname)

        # Add file, at correct path
        zf.write(fpath, zip_path)

    response = StreamingHttpResponse(zf, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s' % urllib.quote_plus(zip_filename.encode('utf-8'))
    return response
