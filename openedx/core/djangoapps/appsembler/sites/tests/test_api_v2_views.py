"""
Tests for the Apppsembler API views.
"""
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from openedx.core.djangolib.testing.utils import skip_unless_lms

from openedx.core.djangoapps.appsembler.sites.api_v2 import SiteCreateView


@skip_unless_lms
@patch.object(SiteCreateView, 'permission_classes', [])  # Skip AMC API key check
class TestSiteCreateView(APITestCase):
    """
    Tests for Platform 2.0 Site Creation view.
    """

    def setUp(self):
        super().setUp()
        self.url = reverse('tahoe_site_creation_v2')

    def test_create_site(self):
        res = self.client.post(self.url, data={
            'site_uuid': 'ee9894a6-898e-11ec-ab4d-9779d2628f5b',
            'domain': 'blue-site.localhost',
            'short_name': 'blue-site',
        })

        assert res.status_code == status.HTTP_200_OK, 'Should succeed: {res}'.format(
            res=res.content.decode('utf-8'),
        )
