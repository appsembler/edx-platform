"""
APIs for the Platform 2.0.
"""

import logging

from rest_framework import views, response, status

from openedx.core.lib.api.permissions import ApiKeyHeaderPermission


from .serializers_v2 import TahoeSiteCreationSerializer

log = logging.Logger(__name__)


class TahoeSiteCreateView(views.APIView):
    """
    Site creation API to create a Platform 2.0 Tahoe site.
    """

    serializer_class = TahoeSiteCreationSerializer
    permission_classes = [ApiKeyHeaderPermission]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        site_data = serializer.save()
        return response.Response({
            'message': 'Site created successfully',
            'site_uuid': site_data['site_uuid'],
        }, status=status.HTTP_201_CREATED)
