import beeline
from rest_framework import serializers
from django.core import validators

from openedx.core.djangoapps.site_configuration.models import SiteConfiguration

try:
    from tahoe_sites import api as tahoe_sites_api
except ImportError:
    # Avoid breaking on production due to missing `tahoe_sites` package.
    # This will cause 500 if the TahoeSiteCreationSerializer to be used
    # TODO: Cleanup after Tahoe Sites is deployed to production
    pass

from .tasks import import_course_on_site_creation_after_transaction


ORG_NAME_REGEX = r'^[a-zA-Z0-9\._-]+$'


class TahoeSiteCreationSerializer(serializers.Serializer):
    """
    Platform 2.0 Tahoe site creation serializer.
    """
    site_uuid = serializers.UUIDField(required=False)
    short_name = serializers.CharField(
        required=True,
        help_text=('Organization and site name. Please do not use spaces or special characters. '
                   'Only allowed special character is hyphen (-).'),
        validators=[
            validators.RegexValidator(regex=ORG_NAME_REGEX),
        ],
    )
    domain = serializers.CharField(
        required=True,
        help_text='Full domain name for the Tahoe site e.g. academy.tahoe.appsembler.com or courses.example.com',
    )

    class Meta:
        fields = ('site_uuid', 'short_name', 'domain',)

    @beeline.traced(name='TahoeSiteCreationSerializer.create')
    def create(self, validated_data):
        # assert False, validated_data
        beeline.add_context_field('validated_data', validated_data)
        created_site_data = tahoe_sites_api.create_tahoe_site(
            domain=validated_data['domain'],
            short_name=validated_data['short_name'],
            site_uuid=validated_data.get('site_uuid'),
        )

        site = created_site_data['site']
        organization = created_site_data['organization']

        tahoe_custom_site_config_params = {}
        if hasattr(SiteConfiguration, 'sass_variables'):
            # This works SiteConfiguration with and without our custom
            # fields of: sass_variables and page_elements.
            # TODO: Fix Site Configuration hacks: https://github.com/appsembler/edx-platform/issues/329
            tahoe_custom_site_config_params['page_elements'] = {}
            tahoe_custom_site_config_params['sass_variables'] = {}

        site_config = SiteConfiguration.objects.create(
            site=site,
            enabled=True,
            site_values={},
            **tahoe_custom_site_config_params,
        )

        course_creation_task_scheduled = import_course_on_site_creation_after_transaction(organization)
        return {
            'site_config': site_config,
            'course_creation_task_scheduled': course_creation_task_scheduled,
            **created_site_data,
        }
