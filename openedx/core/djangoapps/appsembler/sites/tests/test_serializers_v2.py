"""
Tests for Platform 2.0 Site Creation serializers view.
"""
import pytest

from django.db import IntegrityError

from openedx.core.djangoapps.appsembler.sites.serializers_v2 import TahoeSiteCreationSerializer

from site_config_client.models import SiteConfigClientEnabled


@pytest.mark.django_db
def test_create_site_serializer_with_uuid():
    """
    Create a site with a UUID to link it with other systems.
    """
    site_uuid = 'ee9894a6-898e-11ec-ab4d-9779d2628f5b'
    serializer = TahoeSiteCreationSerializer(data={
        'site_uuid': site_uuid,
        'domain': 'blue-site.localhost',
        'short_name': 'blue-site-org',
    })

    assert serializer.is_valid()

    site_data = serializer.save()

    assert site_data, 'Site should be created'
    assert site_data['site'].domain == 'blue-site.localhost', 'Site domain should be set correctly'
    assert site_data['site_configuration'], 'Site config should be created'
    assert str(site_data['site_uuid']) == site_uuid, 'Should not generate different site UUID'

    config_flag = SiteConfigClientEnabled.objects.get(site_uuid=site_uuid)
    assert 'blue-site.localhost' in config_flag.note, 'Add the domain name in the notes for easy search.'
    assert 'blue-site-org' in config_flag.note, 'Add the organization name in the notes for easy search.'


@pytest.mark.django_db
def test_create_site_serializer_with_no_uuid():
    """
    Create a site with no UUID, so the UUID should be created automatically.
    """
    serializer = TahoeSiteCreationSerializer(data={
        'domain': 'blue-site.localhost',
        'short_name': 'blue-site',
    })

    assert serializer.is_valid()

    site_data = serializer.save()

    assert site_data, 'Site should be created'
    assert site_data['site'].domain == 'blue-site.localhost', 'Site domain should be set correctly'
    assert site_data['site_configuration'], 'Site config should be created'
    assert not site_data['site_configuration'].site_values, (
        'Should have empty site_values'
    )
    assert site_data['site_uuid'], 'Site uuid is created'


@pytest.mark.django_db
def test_create_site_serializer_invalid_organization_short_name():
    serializer = TahoeSiteCreationSerializer(data={
        'domain': 'blue-site.localhost',
        'short_name': 'blue site',  # space should not be allowed
    })
    assert not serializer.is_valid()


@pytest.mark.django_db
def test_create_site_serializer_duplicate_uuid():
    """
    Should not allow creating two sites with the same UUID.
    """
    site_uuid = 'ee9894a6-898e-11ec-ab4d-9779d2628f5b'
    serializer = TahoeSiteCreationSerializer(data={
        'site_uuid': site_uuid,
        'domain': 'blue-site.localhost',
        'short_name': 'blue-site',
    })
    serializer.is_valid()
    assert serializer.save()

    duplicate_serializer = TahoeSiteCreationSerializer(data={
        'site_uuid': site_uuid,
        'domain': 'red-site.localhost',
        'short_name': 'red-site',
    })
    duplicate_serializer.is_valid()

    with pytest.raises(IntegrityError, match=r'UNIQUE constraint failed'):
        duplicate_serializer.save()
