from django.contrib.sitemaps import Sitemap
from django.db.models.aggregates import Count

from afqvault.apps.afqmaps.models import Image, Collection, AFQMap

class BaseSitemap(Sitemap):
    priority = 0.5

    def lastmod(self, obj):
        return obj.modify_date

    def location(self,obj):
        return obj.get_absolute_url()


class ImageSitemap(BaseSitemap):
    changefreq = "weekly"
    def items(self):
        return Image.objects.filter(collection__private=False)


class CollectionSitemap(BaseSitemap):
    changefreq = "weekly"
    def items(self):
        return Collection.objects.filter(private=False).annotate(num_submissions=Count('basecollectionitem')).filter(num_submissions__gt = 0)
