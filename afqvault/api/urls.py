from django.conf.urls import url
from rest_framework import routers

from .views import (
    AuthUserView, ImageViewSet, AtlasViewSet,
    CollectionViewSet, MyCollectionsViewSet
)

router = routers.DefaultRouter()
router.register(r'images', ImageViewSet)
router.register(r'atlases', AtlasViewSet)
router.register(r'collections', CollectionViewSet,)
router.register(r'my_collections', MyCollectionsViewSet, '')

api_urls = router.urls + [url(r'^user/?$', AuthUserView.as_view(),
                              name='api-auth-user')]
