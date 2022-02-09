"""
Tests for the Apppsembler API views.
"""
import ddt
import pytest
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from django.db import IntegrityError

from openedx.core.djangolib.testing.utils import skip_unless_lms

from openedx.core.djangoapps.appsembler.sites.api_v2 import TahoeSiteCreateView
from openedx.core.djangoapps.appsembler.sites.serializers_v2 import TahoeSiteCreationSerializer


@ddt.ddt
@skip_unless_lms
@patch.object(TahoeSiteCreateView, 'permission_classes', [])  # Skip AMC API key check
class TestTahoeSiteCreateView(APITestCase):
    """
    Tests for Platform 2.0 Site Creation view.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse('tahoe_site_creation_v2')

    def test_create_site_serializer_with_uuid(self):
        site_uuid = 'ee9894a6-898e-11ec-ab4d-9779d2628f5b'
        serializer = TahoeSiteCreationSerializer(data={
            'site_uuid': site_uuid,
            'domain': 'blue-site.localhost',
            'short_name': 'blue-site',
        })

        assert serializer.is_valid()
        site_data = serializer.save()

        assert site_data, 'Site should be created'
        assert site_data['site'].domain == 'blue-site.localhost', 'Site domain should be set correctly'
        assert site_data['site_config'], 'Site config should be created'
        assert str(site_data['site_uuid']) == site_uuid, 'Should not generate different site UUID'

    def test_create_site_serializer_with_no_uuid(self):
        serializer = TahoeSiteCreationSerializer(data={
            'domain': 'blue-site.localhost',
            'short_name': 'blue-site',
        })

        assert serializer.is_valid()
        site_data = serializer.save()

        assert site_data, 'Site should be created'
        assert site_data['site'].domain == 'blue-site.localhost', 'Site domain should be set correctly'
        assert site_data['site_config'], 'Site config should be created'
        assert site_data['site_uuid'], 'Site uuid is created'

    def test_invalid_organization_short_name(self):
        serializer = TahoeSiteCreationSerializer(data={
            'domain': 'blue-site.localhost',
            'short_name': 'blue site',  # space should not be allowed
        })
        assert not serializer.is_valid()

    def test_create_site_serializer_duplicate_uuid(self):
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

    @ddt.data(
        {},
        {'site_uuid': 'ee9894a6-898e-11ec-ab4d-9779d2628f5b'},
    )
    def test_create_site_with_api(self, site_params):
        """
        Test the site creation API.
        """
        res = self.client.post(self.url, {
            'domain': 'blue-site.localhost',
            'short_name': 'blue-site',
            **site_params,
        })

        assert res.status_code == status.HTTP_201_CREATED, 'Should succeed: {res}'.format(
            res=res.content.decode('utf-8'),
        )
        site_data = res.json()

        if 'site_uuid' in site_params:
            assert site_data['site_uuid'] == site_params['site_uuid']
