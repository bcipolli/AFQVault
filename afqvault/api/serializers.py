import os
import json
import pandas as pd
from django.contrib.auth.models import User
from django.forms.utils import ErrorDict, ErrorList
from django.utils.http import urlquote
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField, StringRelatedField

from afqvault.apps.afqmaps.forms import (
    handle_update_ttl_urls,
    ImageValidationMixin,
)

from afqvault.apps.afqmaps.models import (
    Atlas,
    BaseCollectionItem,
    CognitiveAtlasTask,
    CognitiveAtlasContrast,
    Collection,
    AFQMap
)

from afqvault.utils import strip, logical_xor
from afqvault.apps.afqmaps.utils import get_paper_properties


class HyperlinkedFileField(serializers.FileField):

    def to_representation(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(urlquote(value.url))


class HyperlinkedDownloadURL(serializers.RelatedField):

    def to_representation(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value + "download")


class HyperlinkedRelatedURL(serializers.RelatedField):

    def to_representation(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value.get_absolute_url())


class HyperlinkedImageURL(serializers.CharField):

    def to_representation(self, value):
        if value:
            request = self.context.get('request', None)
            return request.build_absolute_uri(value)


class SerializedContributors(serializers.CharField):

    def to_representation(self, value):
        if value:
            return ', '.join([v.username for v in value.all()])


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class ImageSerializer(serializers.HyperlinkedModelSerializer,
                      ImageValidationMixin):

    id = serializers.ReadOnlyField()
    file = HyperlinkedFileField()
    collection = HyperlinkedRelatedURL(read_only=True)
    collection_id = serializers.ReadOnlyField()
    url = HyperlinkedImageURL(source='get_absolute_url',
                              read_only=True)
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = BaseCollectionItem
        exclude = ['polymorphic_ctype']

    def __init__(self, *args, **kwargs):
        super(ImageSerializer, self).__init__(*args, **kwargs)
        initial_data = getattr(self, 'initial_data', None)
        if initial_data:
            self._metadata_dict = self.extract_metadata_fields(
                self.initial_data, self._writable_fields
            )

    def get_file_size(self, obj):
        return obj.file.size

    def to_representation(self, obj):
        """
        Because Image is Polymorphic
        """
        if isinstance(obj, AFQMap):
            serializer = AFQMapSerializer
            image_type = 'statistic_map'
        elif isinstance(obj, Atlas):
            serializer = AtlasSerializer
            image_type = 'atlas'

        orderedDict = serializer(obj, context={
            'request': self.context['request']}).to_representation(obj)
        orderedDict['image_type'] = image_type
        for key, val in orderedDict.iteritems():
            if pd.isnull(val):
                orderedDict[key] = None
        return orderedDict

    def extract_metadata_fields(self, initial_data, writable_fields):
        field_name_set = set(f.field_name for f in writable_fields)
        metadata_field_set = initial_data.viewkeys() - field_name_set
        return {key: initial_data[key] for key in metadata_field_set}

    def validate(self, data):
        self.afni_subbricks = []
        self.afni_tmp = None
        self._errors = ErrorDict()
        self.error_class = ErrorList

        cleaned_data = self.clean_and_validate(data)

        if self.errors:
            raise serializers.ValidationError(self.errors)

        return cleaned_data

    def save(self, *args, **kwargs):
        metadata_dict = getattr(self, '_metadata_dict', None)
        if metadata_dict:
            data = self.instance.data.copy()
            data.update(self._metadata_dict)
            kwargs['data'] = data
        self.is_valid = True
        super(ImageSerializer, self).save(*args, **kwargs)


class EditableAFQMapSerializer(ImageSerializer):
    class Meta:
        model = AFQMap
        read_only_fields = ('collection',)
        exclude = ['polymorphic_ctype', 'ignore_file_warning', 'data']


class AFQMapSerializer(ImageSerializer):
    read_only=True, source="cognitive_contrast_cogatlas")
    map_type = serializers.SerializerMethodField()
    analysis_level = serializers.SerializerMethodField()

    def get_map_type(self, obj):
        return obj.get_map_type_display()

    def get_analysis_level(self, obj):
        return obj.get_analysis_level_display()

    class Meta:
        model = AFQMap
        exclude = ['polymorphic_ctype', 'ignore_file_warning', 'data']

    def value_to_python(self, value):
        if not value:
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    def to_representation(self, obj):
        ret = super(ImageSerializer, self).to_representation(obj)
        for field_name, value in obj.data.items():
            if field_name not in ret:
                ret[field_name] = self.value_to_python(value)
        return ret


class AtlasSerializer(ImageSerializer):

    label_description_file = HyperlinkedFileField()

    class Meta:
        model = Atlas
        exclude = ['polymorphic_ctype']

    def to_representation(self, obj):
        return super(ImageSerializer, self).to_representation(obj)


class EditableAtlasSerializer(ImageSerializer):

    class Meta:
        model = Atlas
        read_only_fields = ('collection',)


class CollectionSerializer(serializers.ModelSerializer):
    url = HyperlinkedImageURL(source='get_absolute_url', read_only=True)
    download_url = HyperlinkedDownloadURL(source='get_absolute_url', read_only=True)
    owner = serializers.ReadOnlyField(source='owner.id')
    images = ImageSerializer(many=True, source='basecollectionitem_set')
    contributors = SerializedContributors(required=False)
    owner_name = serializers.SerializerMethodField()
    number_of_images = serializers.SerializerMethodField('num_im')


    def num_im(self, obj):
        return obj.basecollectionitem_set.count()

    def get_owner_name(self, obj):
        return obj.owner.username

    def validate(self, data):
        doi = strip(data.get('DOI'))
        name = strip(data.get('name'))

        if not self.instance:
            if not (logical_xor(doi, name)):
                raise serializers.ValidationError(
                    'Specify either "name" or "DOI"'
                )

        if doi:
            try:
                (name, authors,
                 paper_url, _, journal_name) = get_paper_properties(doi)
                data['name'] = name
                data['authors'] = authors
                data['paper_url'] = paper_url
                data['journal_name'] = journal_name
            except:
                raise serializers.ValidationError('Could not resolve DOI')
        return data

    class Meta:
        model = Collection
        exclude = ['private_token', 'private', 'images']
        # Override `required` to allow name fetching by DOI
        extra_kwargs = {'name': {'required': False}}
