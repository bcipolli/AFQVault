from django.contrib import admin
from afqvault.apps.afqmaps.models import Collection, Image, AFQMap, Atlas, \
    Comparison, Similarity
from afqvault.apps.afqmaps.forms import AFQMapForm, AtlasForm
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


class ImageAdmin(PolymorphicParentModelAdmin):
    base_model = Image
    child_models = (
        (AFQMap, AFQMapAdmin),
        (Atlas, AtlasAdmin),
    )

admin.site.register(Image, ImageAdmin)
admin.site.register(Collection)
admin.site.register(Comparison)
admin.site.register(Similarity)
