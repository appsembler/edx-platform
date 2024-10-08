"""
Tests for the Apppsembler Platform 2.0 API views.
"""
import json

import inspect

import logging
import pytest
import uuid
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from unittest.mock import patch, Mock

from django.contrib.sites.models import Site
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

import tahoe_sites.api

from student.tests.factories import UserFactory

from openedx.core.djangoapps.appsembler.sites import api_v2

from openedx.core.djangoapps.site_configuration.tests.factories import SiteConfigurationFactory
from organizations.tests.factories import OrganizationFactory

SITES_API_V2_VIEWS = [
    api_v2_view for _name, api_v2_view in inspect.getmembers(api_v2)
    if inspect.isclass(api_v2_view) and issubclass(api_v2_view, APIView)
]


@pytest.fixture
def create_site(client, superuser_with_token):
    """
    Helper to call the create site api with a superuser token.
    """
    _, api_token = superuser_with_token

    def _create_site(site_params):
        return client.post(
            reverse('tahoe_site_creation_v2'),
            data=json.dumps(site_params),
            content_type='application/json',
            HTTP_AUTHORIZATION='Token {}'.format(api_token),
        )

    return _create_site


@pytest.fixture
def site_with_uuid():
    org = OrganizationFactory.create()
    site = Site.objects.create(domain='fake-site')
    tahoe_sites.api.create_tahoe_site_by_link(org, site)
    site_uuid = tahoe_sites.api.get_uuid_by_site(site)
    return site, site_uuid


@pytest.fixture
def superuser_with_token():
    superuser = UserFactory.create(is_staff=True, is_superuser=True)
    token = Token.objects.create(user=superuser)
    api_token = token.key
    assert api_token
    return superuser, api_token


def test_v2_views_count():
    """
    Ensures SITES_API_V2_VIEWS has the right view classes.
    """
    assert SITES_API_V2_VIEWS, 'Sanity check: Should have a list of Sites API views v2.'


@pytest.mark.parametrize('api_v2_view', SITES_API_V2_VIEWS)
def test_v2_views_security_classes(api_v2_view):
    """
    Checks that Sites API v2 module views are only accessible by superusers.

    Should we switch to the API views
    """
    assert api_v2_view.permission_classes == [IsAuthenticated, IsAdminUser]
    assert api_v2_view.authentication_classes == [TokenAuthentication]


@pytest.mark.django_db
def test_compile_sass_view(client, site_with_uuid, superuser_with_token):
    _, api_token = superuser_with_token
    site, site_uuid = site_with_uuid
    site_configuration = SiteConfigurationFactory.build(
        site=site,
        site_values={},
    )
    site_configuration.save()

    url = reverse('tahoe_compile_sass')
    data = {'site_uuid': site_uuid}
    response = client.post(url, data=data, HTTP_AUTHORIZATION='Token {}'.format(api_token))
    content = response.content.decode('utf-8')
    assert response.status_code == status.HTTP_200_OK, content
    response_json = response.json()
    assert response_json.get('successful_sass_compile'), 'Should compile CSS successfully'
    assert 'sass_compile_message' in response_json


@pytest.mark.django_db
def test_compile_sass_view_site_not_found(client, superuser_with_token):
    _, api_token = superuser_with_token
    url = reverse('tahoe_compile_sass')
    data = {'site_uuid': 'ee9894a6-898e-11ec-ab4d-9779d2628f5b'}
    response = client.post(url, data=data, HTTP_AUTHORIZATION='Token {}'.format(api_token))
    content = response.content.decode('utf-8')
    assert response.status_code == status.HTTP_404_NOT_FOUND, content
    response_json = response.json()
    assert not response_json.get('successful_sass_compile'), 'Should compile CSS successfully'
    assert response_json.get('sass_compile_message') == 'Requested site was not found'


@pytest.mark.django_db
@pytest.mark.parametrize('site_params', [
    {},
    {'site_uuid': 'ee9894a6-898e-11ec-ab4d-9779d2628f5b'},
])
def test_tahoe_site_create_view(site_params, create_site):
    """
    Tests for Platform 2.0 Site Creation view.
    """
    res = create_site({
        'domain': 'blue-site.localhost',
        'short_name': 'blue-site',
        'welcome_course_enrollment_emails': ['admin@example.com', 'another_admin@example.com'],
        **site_params,
    })

    assert res.status_code == status.HTTP_201_CREATED, 'Should succeed: {res}'.format(
        res=res.content.decode('utf-8'),
    )
    site_data = res.json()

    assert 'successful_sass_compile' in site_data
    assert 'sass_compile_message' in site_data

    assert uuid.UUID(site_data['site_uuid']), 'Should return a correct uuid'

    assert len(site_data['welcome_course_enrollment_emails']) == 2, 'Should read the email list properly'

    if 'site_uuid' in site_params:
        assert site_data['site_uuid'] == site_params['site_uuid'], 'Should use the explicit UUID if provided.'


@pytest.mark.django_db
@pytest.mark.parametrize('site_params,error_message', [
    [{'site_uuid': 'ee9894a6-898e'}, 'invalid uuid'],
    [{'domain': ''}, 'empty domain'],
    [{'welcome_course_enrollment_emails': 'should.be.a.list@example.com'}, 'emails should be a list'],
    [{'short_name': 'invalid@company$$name'}, 'invalid organization name'],
])
def test_tahoe_site_create_view_invalid_data(site_params, error_message, create_site):
    """
    Tests for Platform 2.0 Site Creation view should fail on invalid data.
    """
    res = create_site({
        'site_uuid': '2eedd2c4-1d3b-11ed-ae91-679fc9b14e07',
        'domain': 'blue-site.localhost',
        'short_name': 'blue-site',
        'welcome_course_enrollment_emails': ['admin@example.com', 'another_admin@example.com'],
        **site_params,
    })
    assert res.status_code == 400, 'Should fail: {} due to {}'.format(res.content.decode('utf-8'), error_message)


@pytest.mark.django_db
@pytest.mark.parametrize('duplicate_param', ['site_uuid', 'domain', 'short_name'])
def test_tahoe_site_create_view_duplicate(create_site, duplicate_param):
    """
    Tests for creating duplicate site params.
    """
    first_site_params = {
        'domain': 'blue-site.localhost',
        'short_name': 'blue-site',
        'site_uuid': 'ef5a7220-1d35-11ed-8087-1b43998bc4e9',
    }

    resp_ok = create_site(first_site_params)

    assert resp_ok.status_code == 201, 'Should create site: {}'.format(resp_ok.content.decode('utf-8'))
    assert resp_ok.json()['site_uuid'] == first_site_params['site_uuid'], 'Should return the same uuid'

    new_params = {
        'domain': 'red-site.localhost',
        'short_name': 'red-site',
        'site_uuid': '7b52149a-1d36-11ed-8d3f-ebbbfff18479',
    }
    new_params[duplicate_param] = first_site_params[duplicate_param]  # Reuse from old site to simulate invalid request
    resp_duplicate = create_site(new_params)
    resp_duplicate_content = resp_duplicate.content.decode('utf-8')
    assert resp_duplicate.status_code == 400, 'Should fail due to duplicate: {}'.format(resp_duplicate_content)

    organization = tahoe_sites.api.get_organization_by_uuid(first_site_params['site_uuid'])
    assert tahoe_sites.api.get_site_by_organization(organization), 'Should have one site'


@pytest.mark.django_db
def test_tahoe_site_create_view_with_learner_token(client):
    """
    Ensure Platform 2.0 Site Creation view not allowed for learners.
    """
    learner = UserFactory.create()
    api_token = Token.objects.create(user=learner).key
    res = client.post(
        reverse('tahoe_site_creation_v2'),
        data={
            'domain': 'blue-site.localhost',
            'short_name': 'blue-site',
        },
        HTTP_AUTHORIZATION='Token {}'.format(api_token),
    )

    assert res.status_code == status.HTTP_403_FORBIDDEN, 'Should not allow learners to use this API: {res}'.format(
        res=res.content.decode('utf-8'),
    )


@pytest.mark.django_db
@patch('openedx.core.djangoapps.appsembler.sites.utils.compile_sass', Mock(return_value='I am working CSS'))
def test_compile_sass_file(caplog, site_with_uuid):
    """
    Test that _main-v2.scss file used when `THEME_VERSION` == tahoe-v2
    """
    site, _ = site_with_uuid
    site_config = SiteConfigurationFactory.build(
        site=site,
        site_values={'THEME_VERSION': 'tahoe-v2'},
    )
    site_config.save()

    caplog.set_level(logging.INFO)
    assert site_config.get_value("THEME_VERSION") == 'tahoe-v2'
    sass_status = site_config.compile_microsite_sass()
    assert sass_status['successful_sass_compile']
    assert 'Sass compile finished successfully' in sass_status['sass_compile_message']
    assert sass_status['scss_file_used'] == '_main-v2.scss', 'Use `_main-v2.scss` due to THEME_VERSION`'
    assert sass_status['site_css_file'] == 'fake-site.css'
    assert sass_status['theme_version'] == 'tahoe-v2'
    assert sass_status['configuration_source'] == 'openedx_site_configuration_model'
