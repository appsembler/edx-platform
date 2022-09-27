"""
URLs for the tiers app (LMS part).

CMS part is in `cms/djangoapps/appsembler_tiers/`.
"""

from django.urls import path

from .lms_views import (
    LMSSiteUnavailableView,
)

urlpatterns = [
    path('site-unavailable/', LMSSiteUnavailableView.as_view(), name='lms_site_unavailable'),
]
