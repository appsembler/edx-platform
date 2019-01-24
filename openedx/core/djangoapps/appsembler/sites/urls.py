from django.conf import settings
from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

from openedx.core.djangoapps.appsembler.sites.api import (
    SiteConfigurationViewSet,
    SiteViewSet,
    FileUploadView,
    SiteCreateView,
    UsernameAvailabilityView,
    DomainAvailabilityView,
    CustomDomainView,
    DomainSwitchView,
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'site-configurations', SiteConfigurationViewSet)
router.register(r'sites', SiteViewSet)

# The API URLs are now determined automatically by the router.
# Additionally, we include the login URLs for the browsable API.
urlpatterns = [
    url(r'^upload_file/', FileUploadView.as_view()),
    url(r'^username/{}/'.format(settings.USERNAME_PATTERN), UsernameAvailabilityView.as_view()),
    url(r'^domain/(?P<subdomain>[\w.@+-]+)/', DomainAvailabilityView.as_view()),
    url(r'^custom_domain/', CustomDomainView.as_view()),
    url(r'^domain_switch/', DomainSwitchView.as_view()),
    url(r'^register/', SiteCreateView.as_view()),
    url(r'^', include(router.urls)),
]
