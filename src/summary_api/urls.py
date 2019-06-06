from rest_framework import routers
from .resources.views import *

router = routers.DefaultRouter()

router.register(r'sites', SummarySiteViewSet, 'site')

api_urls = router.urls
