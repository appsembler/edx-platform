from django.conf import settings
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from .api import (
    CustomDomainView,
    DomainAvailabilityView,
    DomainSwitchView,
    FindUsernameByEmailView,
    HostFilesView,
    FileUploadView,
    SiteConfigurationViewSet,
    SiteCreateView,
    SiteViewSet,
    UsernameAvailabilityView,
)

from . import api_v2

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'site-configurations', SiteConfigurationViewSet)
router.register(r'sites', SiteViewSet)

# The API URLs are now determined automatically by the router.
# Additionally, we include the login URLs for the browsable API.
urlpatterns = [
    path(r'upload_file/', FileUploadView.as_view()),
    re_path(r'username/{}/'.format(settings.USERNAME_PATTERN), UsernameAvailabilityView.as_view()),
    path('find_username_by_email/', FindUsernameByEmailView.as_view(), name='tahoe_find_username_by_email'),
    re_path(r'^domain/(?P<subdomain>[\w.@+-]+)/', DomainAvailabilityView.as_view()),
    path('custom_domain/', CustomDomainView.as_view()),
    path('domain_switch/', DomainSwitchView.as_view()),
    path('register/', SiteCreateView.as_view(), name='tahoe_site_creation'),
    path('v2/compile-sass/', api_v2.CompileSassView.as_view(), name='tahoe_compile_sass'),
    path('v2/create-site/', api_v2.TahoeSiteCreateView.as_view(), name='tahoe_site_creation_v2'),
    path('', include(router.urls)),
]

if settings.APPSEMBLER_FEATURES.get('ENABLE_FILE_HOST_API', True):
    urlpatterns += [
        path('host_files', HostFilesView.as_view()),
    ]
