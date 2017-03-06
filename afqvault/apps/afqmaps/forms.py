import os
import shutil
from cStringIO import StringIO

import nibabel as nb
import numpy as np
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.forms.models import (
    ModelMultipleChoiceField
)

# from form_utils.forms import BetterModelForm

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button
from crispy_forms.layout import Layout
from crispy_forms.layout import Submit
from crispy_forms.bootstrap import TabHolder, Tab

from .models import Collection, Image, User, AFQMap, BaseAFQMap, \
    Atlas

from django.forms.forms import Form
from django.forms.fields import FileField
import tempfile
from afqvault.apps.afqmaps.utils import (
    split_filename, get_paper_properties,
    memory_uploadfile,
    is_thresholded,
    splitext_nii_gz)
from django import forms
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
from django.forms.utils import flatatt
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.base import ContentFile
from django.forms.widgets import HiddenInput
from afqvault import settings
from file_resubmit.admin import AdminResubmitFileWidget
from guardian.shortcuts import get_objects_for_user

# Create the form class.
collection_fieldsets = [
    ('Essentials', {'fields': ['name',
                               'DOI',
                               'description',
                               'full_dataset_url',
                               'contributors',
                               'private'],
                    'legend': 'Essentials'}),
    ('Participants', {'fields': ['subject_age_mean',
                                 'subject_age_min',
                                 'subject_age_max',
                                 'handedness',
                                 'proportion_male_subjects',
                                 'inclusion_exclusion_criteria',
                                 'number_of_rejected_subjects',
                                 'group_comparison',
                                 'group_description'],
                      'legend': 'Subjects'}),
    ('ExperimentalDesign', {
     'fields': ['type_of_design',
                'number_of_imaging_runs',
                'number_of_experimental_units',
                'length_of_runs',
                'length_of_blocks',
                'length_of_trials',
                'optimization',
                'optimization_method'],
     'legend': 'Design'}),
    ('MRI_acquisition', {'fields': ['scanner_make',
                                    'scanner_model',
                                    'field_strength',
                                    'pulse_sequence',
                                    'parallel_imaging',
                                    'field_of_view',
                                    'matrix_size',
                                    'slice_thickness',
                                    'skip_distance',
                                    'acquisition_orientation',
                                    'order_of_acquisition',
                                    'repetition_time',
                                    'echo_time',
                                    'flip_angle'],
                         'legend': 'Acquisition'}),
    ('IntersubjectRegistration', {'fields': [
                                  'used_intersubject_registration',
                                  'intersubject_registration_software',
                                  'intersubject_transformation_type',
                                  'nonlinear_transform_type',
                                  'transform_similarity_metric',
                                  'interpolation_method',
                                  'object_image_type',
                                  'functional_coregistered_to_structural',
                                  'functional_coregistration_method',
                                  'coordinate_space',
                                  'target_template_image',
                                  'target_resolution',
                                  'used_smoothing',
                                  'smoothing_type',
                                  'smoothing_fwhm',
                                  'resampled_voxel_size'],
                                  'legend': 'Registration'}),
    ('Preprocessing', {
     'fields': ['software_package',
                'software_version',
                'order_of_preprocessing_operations',
                'quality_control',
                'used_b0_unwarping',
                'b0_unwarping_software',
                'used_slice_timing_correction',
                'slice_timing_correction_software',
                'used_motion_correction',
                'motion_correction_software',
                'motion_correction_reference',
                'motion_correction_metric',
                'motion_correction_interpolation',
                'used_motion_susceptibiity_correction'],
     'legend': 'Preprocessing'}),
    ('IndividualSubjectModeling', {
     'fields': ['intrasubject_model_type',
                'intrasubject_estimation_type',
                'intrasubject_modeling_software',
                'hemodynamic_response_function',
                'used_temporal_derivatives',
                'used_dispersion_derivatives',
                'used_motion_regressors',
                'used_reaction_time_regressor',
                'used_orthogonalization',
                'orthogonalization_description',
                'used_high_pass_filter',
                'high_pass_filter_method',
                'autocorrelation_model'],
     'legend': '1st Level'}),
    ('GroupModeling', {
     'fields': ['group_model_type',
                'group_estimation_type',
                'group_modeling_software',
                'group_inference_type',
                'group_model_multilevel',
                'group_repeated_measures',
                'group_repeated_measures_method'],
     'legend': '2nd Level'}),
]


collection_row_attrs = {
    'echo_time': {'priority': 1},
    'number_of_rejected_subjects': {'priority': 2},
    'inclusion_exclusion_criteria': {'priority': 3},
    'group_comparison': {'priority': 1},
    'subject_age_max': {'priority': 2},
    'used_dispersion_derivatives': {'priority': 3},
    'used_intersubject_registration': {'priority': 1},
    'intrasubject_estimation_type': {'priority': 1},
    'field_of_view': {'priority': 2},
    'order_of_preprocessing_operations': {'priority': 2},
    'smoothing_type': {'priority': 1},
    'subject_age_min': {'priority': 2},
    'length_of_blocks': {'priority': 2},
    'used_orthogonalization': {'priority': 1},
    'used_b0_unwarping': {'priority': 2},
    'used_temporal_derivatives': {'priority': 2},
    'software_package': {'priority': 1},
    'scanner_model': {'priority': 1},
    'high_pass_filter_method': {'priority': 2},
    'proportion_male_subjects': {'priority': 2},
    'number_of_imaging_runs': {'priority': 2},
    'interpolation_method': {'priority': 2},
    'group_repeated_measures_method': {'priority': 3},
    'motion_correction_software': {'priority': 3},
    'used_motion_regressors': {'priority': 2},
    'functional_coregistered_to_structural': {'priority': 2},
    'motion_correction_interpolation': {'priority': 3},
    'optimization_method': {'priority': 3},
    'hemodynamic_response_function': {'priority': 2},
    'group_model_type': {'priority': 1},
    'used_slice_timing_correction': {'priority': 1},
    'intrasubject_modeling_software': {'priority': 2},
    'target_template_image': {'priority': 2},
    'resampled_voxel_size': {'priority': 3},
    'object_image_type': {'priority': 1},
    'group_description': {'priority': 2},
    'functional_coregistration_method': {'priority': 3},
    'length_of_trials': {'priority': 2},
    'handedness': {'priority': 2},
    'used_motion_correction': {'priority': 1},
    'pulse_sequence': {'priority': 1},
    'used_high_pass_filter': {'priority': 1},
    'orthogonalization_description': {'priority': 2},
    'acquisition_orientation': {'priority': 2},
    'order_of_acquisition': {'priority': 3},
    'group_repeated_measures': {'priority': 1},
    'motion_correction_reference': {'priority': 3},
    'group_model_multilevel': {'priority': 3},
    'number_of_experimental_units': {'priority': 2},
    'type_of_design': {'priority': 1},
    'coordinate_space': {'priority': 1},
    'transform_similarity_metric': {'priority': 3},
    'repetition_time': {'priority': 1},
    'slice_thickness': {'priority': 1},
    'length_of_runs': {'priority': 2},
    'software_version': {'priority': 1},
    'autocorrelation_model': {'priority': 2},
    'b0_unwarping_software': {'priority': 3},
    'intersubject_transformation_type': {'priority': 1},
    'quality_control': {'priority': 3},
    'used_smoothing': {'priority': 1},
    'smoothing_fwhm': {'priority': 1},
    'intrasubject_model_type': {'priority': 1},
    'matrix_size': {'priority': 2},
    'optimization': {'priority': 2},
    'group_inference_type': {'priority': 1},
    'subject_age_mean': {'priority': 1},
    'used_motion_susceptibiity_correction': {'priority': 3},
    'group_statistic_type': {'priority': 2},
    'skip_distance': {'priority': 2},
    'used_reaction_time_regressor': {'priority': 2},
    'group_modeling_software': {'priority': 2},
    'parallel_imaging': {'priority': 3},
    'intersubject_registration_software': {'priority': 2},
    'nonlinear_transform_type': {'priority': 2},
    'field_strength': {'priority': 1},
    'group_estimation_type': {'priority': 1},
    'target_resolution': {'priority': 1},
    'slice_timing_correction_software': {'priority': 3},
    'scanner_make': {'priority': 1},
    'group_smoothness_fwhm': {'priority': 1},
    'flip_angle': {'priority': 2},
    'group_statistic_parameters': {'priority': 3},
    'motion_correction_metric': {'priority': 3},
}


class ContributorCommaSepInput(forms.Widget):

    def render(self, name, value, attrs=None):
        final_attrs = self.build_attrs(attrs, type='text', name=name)
        if not type(value) == unicode and value is not None:
            out_vals = []
            for val in value:
                try:
                    out_vals.append(str(User.objects.get(pk=val).username))
                except:
                    continue
            value = ', '.join(out_vals)
            if value:
                final_attrs['value'] = smart_str(value)
        else:
            final_attrs['value'] = smart_str(value)
        return mark_safe(u'<input%s />' % flatatt(final_attrs))


class ContributorCommaField(ModelMultipleChoiceField):
    widget = ContributorCommaSepInput

    def clean(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []

        split_vals = [v.strip() for v in value.split(',')]

        if not isinstance(split_vals, (list, tuple)):
            raise ValidationError("Invalid input.")

        for name in split_vals:
            if not len(self.queryset.filter(username=name)):
                raise ValidationError("User %s does not exist." % name)

        return self.queryset.filter(username__in=split_vals)


class CollectionForm(ModelForm):

    class Meta:
        exclude = ('owner', 'private_token', 'contributors', 'private')
        model = Collection
        # fieldsets = study_fieldsets
        # row_attrs = study_row_attrs

    def clean(self):
        cleaned_data = super(CollectionForm, self).clean()
        doi = self.cleaned_data['DOI']
        if doi.strip() == '':
            self.cleaned_data['DOI'] = None

        if self.cleaned_data['DOI']:
            self.cleaned_data['DOI'] = self.cleaned_data['DOI'].strip()
            try:
                self.cleaned_data["name"], self.cleaned_data["authors"], self.cleaned_data[
                    "paper_url"], _, self.cleaned_data["journal_name"] = get_paper_properties(self.cleaned_data['DOI'].strip())
            except:
                self._errors["DOI"] = self.error_class(
                    ["Could not resolve DOI"])
            else:
                if "name" in self._errors:
                    del self._errors["name"]
        elif "name" not in cleaned_data or not cleaned_data["name"]:
            self._errors["name"] = self.error_class(
                ["You need to set the name or the DOI"])
            self._errors["DOI"] = self.error_class(
                ["You need to set the name or the DOI"])

        return cleaned_data

    def __init__(self, *args, **kwargs):

        super(CollectionForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.layout = Layout()
        tab_holder = TabHolder()
        for fs in collection_fieldsets:
            # manually enforce field exclusion
            fs[1]['fields'] = [
                v for v in fs[1]['fields'] if v not in self.Meta.exclude]
            tab_holder.append(Tab(fs[1]['legend'], *fs[1]['fields']))
        self.helper.layout.extend([tab_holder, Submit(
                                  'submit', 'Save', css_class="btn-large offset2")])


class OwnerCollectionForm(CollectionForm):
    contributors = ContributorCommaField(
        queryset=None, required=False, help_text="Select other AFQVault users to add as contributes to the collection.  Contributors can add, edit and delete images in the collection.")

    class Meta():
        exclude = ('owner', 'private_token')
        model = Collection
        widgets = {
            'private': forms.RadioSelect
        }

    def __init__(self, *args, **kwargs):
        super(OwnerCollectionForm, self).__init__(*args, **kwargs)
        self.fields['contributors'].queryset = User.objects.exclude(
            pk=self.instance.owner.pk)


class ImageValidationMixin(object):

    def clean_and_validate(self, cleaned_data):
        print "enter clean_and_validate"
        file = cleaned_data.get('file')
        print file
        if file:
            # check extension of the data file
            print file.name, file.file
            _, fname, ext = split_filename(file.name)
            if not ext.lower() in Image.allowed_extensions:
                self._errors["file"] = self.error_class(
                    ["Doesn't have proper extension (%s)" % ','.join(Image.allowed_extensions)]
                )
                del cleaned_data["file"]
                return cleaned_data

            # prepare file to loading into memory
            try:
                tmp_dir = tempfile.mkdtemp()
                tmp_file = os.path.join(tmp_dir, file.name)
                with open(tmp_file, 'wb') as fp:
                    fp.write(file.file.read())

                print "updating file in cleaned_data"

                cleaned_data['file'] = memory_uploadfile(
                    tmp_file, file.name, cleaned_data['file']
                )
            finally:
                try:
                    shutil.rmtree(tmp_dir)
                except OSError as exc:
                    if exc.errno != 2:  # code 2 - no such file or directory
                        raise  # re-raise exception

        elif not getattr(self, 'partial', False):
            # Skip validation error if this is a partial update from the API
            raise ValidationError("Couldn't read uploaded file")

        return cleaned_data


class ImageForm(ModelForm, ImageValidationMixin):
    def __init__(self, *args, **kwargs):
        ModelForm.__init__(self, *args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False

    class Meta:
        model = Image
        exclude = []
        widgets = {
            'file': AdminResubmitFileWidget,
            'data_origin': HiddenInput
        }

    def clean(self, **kwargs):
        cleaned_data = super(ImageForm, self).clean()
        cleaned_data["tags"] = clean_tags(cleaned_data)
        return self.clean_and_validate(cleaned_data)


class AFQMapForm(ImageForm):

    def __init__(self, *args, **kwargs):
        super(AFQMapForm, self).__init__(*args, **kwargs)
        self.helper.form_tag = False
        self.helper.add_input(Submit('submit', 'Submit'))

    def clean(self, **kwargs):
        cleaned_data = super(AFQMapForm, self).clean()

        cleaned_data["is_valid"] = True  # This will be only saved if the form will validate
        cleaned_data["tags"] = clean_tags(cleaned_data)
        print cleaned_data

        return cleaned_data

    class Meta(ImageForm.Meta):
        model = AFQMap
        fields = ('name', 'collection', 'description', 'map_type', 'modality',
                  'analysis_level', 'number_of_subjects', 'figure',
                  'file', 'ignore_file_warning', 'tags', 'statistic_parameters',
                  'smoothness_fwhm', 'is_thresholded', 'perc_bad_voxels', 'is_valid', 'data_origin')
        widgets = {
            'file': AdminResubmitFileWidget,
            'is_thresholded': HiddenInput,
            'ignore_file_warning': HiddenInput,
            'perc_bad_voxels': HiddenInput,
            'not_mni': HiddenInput,
            'brain_coverage': HiddenInput,
            'perc_voxels_outside': HiddenInput,
            'is_valid': HiddenInput,
            'data_origin': HiddenInput
        }


class AtlasForm(ImageForm):

    class Meta(ImageForm.Meta):
        model = Atlas
        fields = ('name', 'collection', 'description', 'figure',
                  'file', 'label_description_file', 'tags')


class PolymorphicImageForm(ImageForm):

    def __init__(self, *args, **kwargs):
        super(PolymorphicImageForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        if self.instance.polymorphic_ctype is not None:
            if self.instance.polymorphic_ctype.model == 'atlas':
                self.fields = AtlasForm.base_fields
            else:
                self.fields = AFQMapForm.base_fields

    def clean(self, **kwargs):
        if "label_description_file" in self.fields.keys():
            use_form = AtlasForm
        elif "map_type" in self.fields.keys():
            use_form = AFQMapForm
        else:
            raise Exception("unknown image type! %s" % str(self.fields.keys()))

        new_instance = use_form(self)
        new_instance.cleaned_data = self.cleaned_data
        new_instance._errors = self._errors
        self.fields = new_instance.fields
        return new_instance.clean()


class EditAFQMapForm(AFQMapForm):

    def __init__(self, *args, **kwargs):
        user = kwargs['user']
        del kwargs['user']
        super(EditAFQMapForm, self).__init__(*args, **kwargs)
        if user.is_superuser:
            self.fields['collection'].queryset = Collection.objects.all()
        else:
            self.fields['collection'].queryset = get_objects_for_user(
                user, 'afqmaps.change_collection')


class AddAFQMapForm(AFQMapForm):

    class Meta(AFQMapForm.Meta):
        fields = ('name', 'description', 'map_type', 'modality',
                  'analysis_level', 'number_of_subjects', 'figure',
                  'file', 'ignore_file_warning', 'tags', 'statistic_parameters',
                  'smoothness_fwhm', 'is_thresholded', 'perc_bad_voxels', 'data_origin')


class EditAtlasForm(AtlasForm):

    def __init__(self, *args, **kwargs):
        user = kwargs['user']
        del kwargs['user']
        super(EditAtlasForm, self).__init__(*args, **kwargs)
        self.helper.form_tag = True
        self.helper.add_input(Submit('submit', 'Submit'))
        if user.is_superuser:
            self.fields['collection'].queryset = Collection.objects.all()
        else:
            self.fields['collection'].queryset = get_objects_for_user(
                user, 'afqmaps.change_collection')

    class Meta(AtlasForm.Meta):
        exclude = ()


class SimplifiedAFQMapForm(EditAFQMapForm):

    class Meta(EditAFQMapForm.Meta):
        fields = ('name', 'collection', 'description', 'map_type', 'modality',
                  'file', 'ignore_file_warning', 'tags', 'is_thresholded',
                  'perc_bad_voxels')


class NeuropowerAFQMapForm(EditAFQMapForm):
    def __init__(self, *args, **kwargs):
        super(NeuropowerAFQMapForm, self).__init__(*args, **kwargs)
        self.fields['analysis_level'].required = True
        self.fields['number_of_subjects'].required = True

    class Meta(EditAFQMapForm.Meta):
        fields = ('name', 'collection', 'description', 'map_type', 'modality', 'map_type', 'analysis_level', 'number_of_subjects',
                  'file', 'ignore_file_warning', 'tags', 'is_thresholded',
                  'perc_bad_voxels')


class UploadFileForm(Form):

    # TODO Need to upload in a temp directory
    # (upload_to="images/%s/%s"%(instance.collection.id, filename))
    file = FileField(required=False)

    def __init__(self, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.file = ''

    def clean(self):
        cleaned_data = super(UploadFileForm, self).clean()
        file = cleaned_data.get("file")
        if file:
            ext = os.path.splitext(file.name)[1]
            ext = ext.lower()
            if ext not in ['.zip', '.gz']:
                raise ValidationError("Not allowed filetype!")


class PathOnlyWidget(forms.Widget):

    def render(self, name, value, attrs=None):
        return mark_safe('<a target="_blank" href="%s">%s</a><br /><br />' % (value.url, value.url))


class MapTypeListWidget(forms.Widget):

    def render(self, name, value, attrs=None):
        map_type = [
            v for k, v in BaseAFQMap.MAP_TYPE_CHOICES if k == value].pop()
        input = '<input type="hidden" name="%s" value="%s" />' % (name, value)
        return mark_safe('%s<strong>%s</strong><br /><br />' % (input, map_type))


def clean_tags(self):
    """
    Force all tags to lowercase.
    """
    tags = self.get('tags', None)
    if tags:
        tags = [t.lower() for t in tags]

    return tags
