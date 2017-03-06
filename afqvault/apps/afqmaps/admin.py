from django.contrib import admin
from afqvault.apps.afqmaps.models import Collection, Image, AFQMap, Atlas, \
    NIDMResults, NIDMResultAFQMap, Comparison, Similarity
from afqvault.apps.afqmaps.forms import AFQMapForm, AtlasForm, \
    NIDMResultAFQMapForm, NIDMResultsForm
from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin


class BaseImageAdmin(admin.ModelAdmin):
    readonly_fields = ['collection']

    # enforce read only only on edit
    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj else []


class AFQMapAdmin(PolymorphicChildModelAdmin, BaseImageAdmin):
    base_model = AFQMap
    base_form = AFQMapForm


class AtlasAdmin(PolymorphicChildModelAdmin, BaseImageAdmin):
    base_model = Atlas
    base_form = AtlasForm


class NIDMAFQMapAdmin(PolymorphicChildModelAdmin, BaseImageAdmin):
    base_model = NIDMResultAFQMap
    base_form = NIDMResultAFQMapForm
    readonly_fields = BaseImageAdmin.readonly_fields + ['nidm_results']


class ImageAdmin(PolymorphicParentModelAdmin):
    base_model = Image
    child_models = (
        (AFQMap, AFQMapAdmin),
        (Atlas, AtlasAdmin),
        (NIDMResultAFQMap, NIDMAFQMapAdmin)
    )


class NIDMResultsAdmin(BaseImageAdmin):
    form = NIDMResultsForm

    def save_model(self, request, obj, form, change):
        instance = form.save(commit=False)
        instance.save()
        form.save_nidm()
        form.update_ttl_urls()
        form.save_m2m()

admin.site.register(Image, ImageAdmin)
admin.site.register(Collection)
admin.site.register(NIDMResults,NIDMResultsAdmin)
admin.site.register(Comparison)
admin.site.register(Similarity)
