from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, TemplateView
from django.views.generic.base import RedirectView

from afqvault import settings
from afqvault.apps.afqmaps.models import KeyValueTag
from afqvault.apps.afqmaps.views import ImagesInCollectionJson,\
    PublicCollectionsJson, MyCollectionsJson, AtlasesAndParcellationsJson
from .views import edit_collection, view_image, delete_image, edit_image, \
                view_collection, delete_collection, download_collection, upload_folder, add_image_for_neurosynth, \
                serve_image, add_image, \
                papaya_js_embed, view_images_by_tag, add_image_for_neuropower, \
                stats_view, \
                find_similar, find_similar_json, compare_images, edit_metadata, \
                export_images_filenames, search, gene_expression_json, \
                gene_expression


urlpatterns = patterns('',
    url(r'^my_collections/$',
        login_required(TemplateView.as_view(template_name='afqmaps/my_collections.html.haml')),
        name='my_collections'),
    url(r'^my_collections/json$',
        login_required(MyCollectionsJson.as_view()),
        name='my_collections_json'),
    url(r'^collections/$',
        TemplateView.as_view(template_name='afqmaps/collections_index.html.haml'),
        name='collections_list'),
    url(r'^collections/json$',
        PublicCollectionsJson.as_view(),
        name='collections_list_json'),
    url(r'^collections/stats$',
        stats_view,
        name='collections_stats'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/$',
        view_collection,
        name='collection_details'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/json$',
        ImagesInCollectionJson.as_view(),
        name='collection_images_json'),
    url(r'^collections/new$',
        edit_collection,
        name='new_collection'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/edit$',
        edit_collection,
        name='edit_collection'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/delete$',
        delete_collection,
        name='delete_collection'),
    url(r'^collections/(?P<cid>\d+|[A-Z]{8})/download$',
       download_collection,
       name='download_collection'),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/addimage',
        add_image,
        name="add_image"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/upload_folder$',
        upload_folder,
        name="upload_folder"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/images/(?P<pk>\d+)/$',
        view_image,
        name="private_image_details"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/export/imagesfilenames$',
        export_images_filenames,
        name="export_images_filenames"),
    url(r'^collections/(?P<collection_cid>\d+|[A-Z]{8})/editmetadata$',
        edit_metadata,
        name="edit_metadata"),
    url(r'^atlases/$', TemplateView.as_view(template_name="afqmaps/atlases.html"),
        name="atlases_and_parcellations"),
    url(r'^atlases2/$', TemplateView.as_view(template_name="afqmaps/atlases2.html"),
        name="atlases_and_parcellations2"),
    url(r'^atlases/json$',
        AtlasesAndParcellationsJson.as_view(),
        name='atlases_and_parcellations_json'),
    url(r'^images/tags/$',
        ListView.as_view(
            queryset=KeyValueTag.objects.all(),
            context_object_name='tags',
            template_name='afqmaps/tags_index.html.haml'),
        name='tags_list'),
    url(r'^images/tags/(?P<tag>[A-Za-z0-9@\.\+\-\_\s]+)/$',
        view_images_by_tag,
        name='images_by_tag'),
    url(r'^images/(?P<pk>\d+)/$',
        view_image,
        name='image_details'),
    url(r'^images/(?P<pk>\d+)/edit$',
        edit_image,
        name='edit_image'),
    url(r'^images/(?P<pk>\d+)/delete$',
        delete_image,
        name='delete_image'),
    url(r'^images/add_for_neurosynth$',
        add_image_for_neurosynth,
        name='add_for_neurosynth'),
    url(r'^images/add_for_neuropower$',
        add_image_for_neuropower,
        name='add_for_neuropower'),
    url(r'^images/(?P<pk>\d+)/js/embed$',
        papaya_js_embed,
        name='papaya_js_embed'),

    url(r'^images/(?P<pk>\d+)/papaya/embedview$',
        papaya_js_embed,
        {'iframe':True},name='papaya_iframe_embed'),

    url(r'^media/images/(?P<collection_cid>\d+|[A-Z]{8})/(?P<img_name>[0-9a-zA-Z\^\&\'\@\{\}\[\]\,\$\=\!\-\#\(\)\.\%\+\~\_ ]+)$',
        serve_image,
        name='serve_image'),

    # Compare images and search
    url(r'^images/compare/(?P<pk1>\d+)/(?P<pk2>\d+)$',
        compare_images,
        name='compare_images'),
    url(r'^images/(?P<pk>\d+)/find_similar$',
        find_similar,
        name='find_similar'),
    url(r'^images/(?P<pk>\d+)/find_similar/json/$',
        find_similar_json,
        name='find_similar_json'),

    url(r'^images/(?P<pk>\d+)/gene_expression$',
        gene_expression,
        name='gene_expression'),
    url(r'^images/(?P<pk>\d+)/gene_expression/json$',
        gene_expression_json,
        name='gene_expression_json'),
    url(r'^search$',
        search,
        name='search'),
)
