import beeline
from rest_framework import serializers

from openedx.core.djangoapps.site_configuration.models import SiteConfiguration

try:
    from tahoe_sites import api as tahoe_sites_api
except ImportError:
    # Avoid breaking on production due to missing `tahoe_sites` package.
    # This will cause 500 if the SiteCreationSerializer to be used
    # TODO: Cleanup after Tahoe Sites is deployed to production
    pass

from .tasks import import_course_on_site_creation_after_transaction


class SiteCreationSerializer(serializers.Serializer):
    """
    Platform 2.0 sit creation serializer.
    """
    uuid = serializers.UUIDField()
    short_name = serializers.CharField()
    domain = serializers.CharField()

    @beeline.traced(name='SiteCreationSerializer.create')
    def create(self, validated_data):
        beeline.add_context_field('validated_data', validated_data)
        site = tahoe_sites_api.create_site(**validated_data)
        organization = tahoe_sites_api.get_organization_by_uuid(validated_data['uuid'])

        tahoe_custom_site_config_params = {}
        if hasattr(SiteConfiguration, 'sass_variables'):
            # This works SiteConfiguration with and without our custom
            # fields of: sass_variables and page_elements.
            # TODO: Cleanup after using upstream `edx-organizations` package
            tahoe_custom_site_config_params['page_elements'] = {}
            tahoe_custom_site_config_params['sass_variables'] = {}

        SiteConfiguration.objects.create(
            site=site,
            enabled=True,
            site_values={},
            **tahoe_custom_site_config_params,
        )

        import_course_on_site_creation_after_transaction(organization)
