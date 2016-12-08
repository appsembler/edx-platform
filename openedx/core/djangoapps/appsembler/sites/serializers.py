from django.contrib.sites.models import Site
from rest_framework import serializers
from organizations import api as organizations_api
from organizations.models import Organization
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration

from .utils import sass_to_dict, dict_to_sass
from .tasks import bootstrap_site


class SASSDictField(serializers.DictField):
    def to_internal_value(self, data):
        return dict_to_sass(data)

    def to_representation(self, value):
        return sass_to_dict(value)


class SiteConfigurationSerializer(serializers.ModelSerializer):
    values = serializers.DictField()
    sassVariables = serializers.ListField(source='sass_variables')
    pageElements = serializers.DictField(source='page_elements')

    class Meta:
        model = SiteConfiguration
        fields = ('id', 'values', 'sassVariables', 'pageElements')

    def update(self, instance, validated_data):
        object = super(SiteConfigurationSerializer, self).update(instance, validated_data)
        # TODO: make this per-site, not scalable in production
        Site.objects.clear_cache()
        return object


class SiteConfigurationListSerializer(SiteConfigurationSerializer):
    class Meta(SiteConfigurationSerializer.Meta):
        fields = ('id', 'name', 'domain')


class SiteSerializer(serializers.ModelSerializer):
    configuration = SiteConfigurationSerializer(read_only=True)

    class Meta:
        model = Site
        fields = ('id', 'name', 'domain', 'configuration')

    def create(self, validated_data):
        site = super(SiteSerializer, self).create(validated_data)
        task = bootstrap_site.delay(site)
        return {'task_id': task.id}


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id', 'name', 'short_name')

    def create(self, validated_data):
        return organizations_api.add_organization(**validated_data)


class RegistrationSerializer(serializers.Serializer):
    site = SiteSerializer()
    organization = OrganizationSerializer()
    user_email = serializers.EmailField(required=False)

    def create(self, validated_data):
        site_data = validated_data.pop('site')
        site = Site.objects.create(**site_data)
        organization_data = validated_data.pop('organization')
        user_email = validated_data.pop('user_email', None)
        task = bootstrap_site.delay(site, organization_data.get('name'), user_email)
        return {
            'task_id': task.id,
        }

