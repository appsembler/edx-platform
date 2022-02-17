"""
APIs for the Platform 2.0.
"""

import logging

from rest_framework import views, status
from rest_framework.response import Response

import tahoe_sites.api

from openedx.core.lib.api.permissions import ApiKeyHeaderPermission
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration

from .serializers_v2 import TahoeSiteCreationSerializer


log = logging.Logger(__name__)


class CompileSassView(views.APIView):
    """
    Compiles Tahoe Site Sass via API by:
        - initializing the `api_adapter` for the site
        - calling SiteConfiguration.compile_microsite_sass()

    Usage:

        POST /appsembler/api/compile_sass/
            {"site_uuid": "fake-site-uuid"}
    """
    permission_classes = (ApiKeyHeaderPermission,)

    def post(self, request, format=None):
        site_uuid = request.data['site_uuid']
        site = tahoe_sites.api.get_site_by_uuid(site_uuid)
        configuration = SiteConfiguration.objects.get(site=site)
        configuration.init_api_client_adapter(site)
        sass_status = configuration.compile_microsite_sass()

        if sass_status['successful_sass_compile']:
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(sass_status, status=status_code)


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

        # Make some of the fields serializable
        site_data['organization'] = site_data['organization'].short_name
        site_data['site'] = site_data['site'].domain
        del site_data['site_configuration']  # Useless for the API caller

        return Response({
            'message': 'Site created successfully',
            **site_data,
        }, status=status.HTTP_201_CREATED)
