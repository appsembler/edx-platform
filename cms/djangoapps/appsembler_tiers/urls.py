"""
URLs for the tiers app to be included in the LMS.
"""

from django.urls import path

from cms.djangoapps.appsembler_tiers.views import (
    SiteUnavailableRedirectView,
)

urlpatterns = [
    path('site-unavailable/', SiteUnavailableRedirectView.as_view(), name='site_unavailable'),
]
