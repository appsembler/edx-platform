"""
APIs for the Platform 2.0.
"""

import logging
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import views, status
from rest_framework.response import Response

import tahoe_sites.api

from sass import CompileError
import os
import sass

from openedx.core.lib.api.permissions import ApiKeyHeaderPermission
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration

from django.conf import settings
from django.contrib.sites.models import Site
from openedx.core.djangoapps.theming.models import SiteTheme

from openedx.core.djangoapps.appsembler.sites import utils as sites_utils

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

        try:
            site = tahoe_sites.api.get_site_by_uuid(site_uuid)
        except ObjectDoesNotExist:
            return Response({
                'successful_sass_compile': False,
                'sass_compile_message': 'Requested site was not found',
            }, status=status.HTTP_404_NOT_FOUND)

        configuration = SiteConfiguration.objects.get(site=site)
        configuration.init_api_client_adapter(site)
        sass_status = configuration.compile_microsite_sass()

        if sass_status['successful_sass_compile']:
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(sass_status, status=status_code)




class MatejTerribleCompileSassView(views.APIView):
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
        sass_variables = request.data['sass_variables']

        scss_file = 'main-v2.scss'

        try:
            css_output = sites_utils.compile_sass(scss_file, sass_variables=sass_variables)
            successful_sass_compile = True
            sass_compile_message = 'Sass compile finished successfully for site {site}'.format(site=self.site.domain)
        except CompileError as exc:
            successful_sass_compile = False
            sass_compile_message = 'Sass compile failed for site {site} with the error: {message}'.format(
                site=self.site.domain,
                message=str(exc),
            )

        if successful_sass_compile:
            status_code = status.HTTP_200_OK
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        return Response({
            'message': sass_compile_message,
            'compiled_css': css_output,
        }, status=status_code)


    def compile_sass(sass_file, sass_variables=None):
        from openedx.core.djangoapps.theming.helpers import get_theme_base_dir, Theme
        try:
            default_site = Site.objects.get(id=settings.SITE_ID)
        except Site.DoesNotExist:
            # Empty CSS output if the database isn't initialized yet.
            # This unblocks migrations and other cases before having a default site.
            return ''

        def _formatted_sass_variables():
            return " ".join(["{}: {};".format(var, val['value']) for var, val in sass_variables])

        def _sass_var_override(path):
            if 'branding-basics' in path:
                return [(path, _formatted_sass_variables())]

        site_theme = SiteTheme(site=default_site, theme_dir_name=settings.DEFAULT_SITE_THEME)
        theme = Theme(
            name=site_theme.theme_dir_name,
            theme_dir_name=site_theme.theme_dir_name,
            themes_base_dir=get_theme_base_dir(site_theme.theme_dir_name),
            project_root=settings.PROJECT_ROOT,
        )
        sass_var_file = os.path.join(theme.path, 'static', 'sass', sass_file)
        customer_specific_includes = os.path.join(theme.customer_specific_path, 'static', 'sass')
        importers = None
        if sass_variables:
            importers = [(0, _sass_var_override)]
        css_output = sass.compile(
            filename=sass_var_file,
            include_paths=[customer_specific_includes],
            importers=importers
        )
        return css_output


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
