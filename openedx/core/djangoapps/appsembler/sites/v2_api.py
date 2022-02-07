"""
APIs for the Platform 2.0.
"""

import logging

from rest_framework import generics

from openedx.core.lib.api.permissions import ApiKeyHeaderPermission


from .serializers_v2 import SiteCreationSerializer

log = logging.Logger(__name__)


class SiteCreateView(generics.CreateAPIView):
    serializer_class = SiteCreationSerializer
    permission_classes = [ApiKeyHeaderPermission]
