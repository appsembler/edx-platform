"""
Tests for the Apppsembler API views.
"""
import pytest
from mock import patch

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from edx_rest_framework_extensions.auth.session.authentication import SessionAuthenticationAllowInactiveUser
from openedx.core.djangoapps.appsembler.sites.utils import make_amc_admin
from openedx.core.djangoapps.site_configuration.tests.factories import SiteConfigurationFactory
from organizations.tests.factories import OrganizationFactory
from rest_framework import status
from rest_framework.test import APITestCase

from openedx.core.djangoapps.appsembler.sites import (
    site_config_client_helpers as client_helpers,
)
from openedx.core.djangolib.testing.utils import skip_unless_lms
from openedx.core.djangoapps.appsembler.multi_tenant_emails.tests.test_utils import (
    with_organization_context,
    create_org_user,
)


@skip_unless_lms
@patch(
    # Skip AMC API key check
    'openedx.core.djangoapps.appsembler.sites.api.FindUsernameByEmailView.permission_classes', []
)
class TestFindUsernameByEmailView(APITestCase):
    """
    Tests for the FindUsernameOnOrg view.
    """

    def setUp(self):
        super(TestFindUsernameByEmailView, self).setUp()
        self.url = reverse('tahoe_find_username_by_email')

    def get_username(self, email, organization_name):
        """
        Fetch username via the FindUsernameOnOrg view.
        """
        return self.client.get(self.url, {
            'email': email,
            'organization_name': organization_name,
        })

    def test_find_username(self):
        """
        Test happy scenario.
        """
        email = 'learner@red.org'
        username = 'learner_xyz'
        with with_organization_context(site_color='red1') as red_org:
            create_org_user(red_org, email=email, username=username)

        response = self.get_username(email, red_org.name)
        assert response.status_code == status.HTTP_200_OK, response.content.decode('utf-8')
        assert response.json()['username'] == username

    def test_organization_separation(self):
        """
        Test organization collision.
        """
        color1 = 'red1'
        email = 'learner@red.org'
        username = 'learner_xyz'
        with with_organization_context(site_color=color1) as red_org:
            create_org_user(red_org, email=email, username=username)

        with with_organization_context(site_color='blue1') as blue_org:
            pass

        response = self.get_username(email, blue_org.name)
        assert response.status_code == status.HTTP_404_NOT_FOUND, response.content.decode('utf-8')  # Should keep sites separated

        blue_user = create_org_user(blue_org, email=email)
        response = self.get_username(email, blue_org.name)
        assert response.status_code == status.HTTP_200_OK, response.content.decode('utf-8')
        assert response.json()['username'] == blue_user.username

    def test_not_found(self):
        """
        Test missing email.
        """
        with with_organization_context(site_color='empty_org') as red_org:
            pass

        response = self.get_username('nobody@example.com', red_org.name)
        assert response.status_code == status.HTTP_404_NOT_FOUND, response.content.decode('utf-8')


@skip_unless_lms
@patch(
    'openedx.core.djangoapps.appsembler.sites.api.SiteViewSet.authentication_classes',
    [SessionAuthenticationAllowInactiveUser]
)
class TestSiteViewSet(APITestCase):
    """
    Tests for the SiteViewSet AMC API.
    """
    def setUp(self):
        super(TestSiteViewSet, self).setUp()
        self.url = reverse('site-list')
        self.color = 'red'
        with with_organization_context(site_color=self.color) as red_org:
            self.red_org = red_org
            self.admin = create_org_user(
                organization=red_org,
                is_amc_admin=True,
                email='red@example.com',
                username=self.color,
                password=self.color
            )

    def test_list_sites(self):
        with with_organization_context(site_color=self.color):
            assert self.client.login(username=self.admin.username, password=self.color)
            response = self.client.get(
                self.url,
            )
            content = response.content.decode('utf-8')
            assert response.status_code == status.HTTP_200_OK, content


@pytest.fixture
def site_with_org(scope='function'):
    org = OrganizationFactory.create()
    assert org.edx_uuid, 'Should have valid uuid'
    site = Site.objects.create(domain='fake-site')
    site.organizations.add(org)
    return site, org


@pytest.mark.django_db
def test_compile_sass_view(client, monkeypatch, site_with_org):
    monkeypatch.setattr(client_helpers, 'CONFIG_CLIENT_INSTALLED', True)
    site, org = site_with_org
    site_configuration = SiteConfigurationFactory.build(site=site)
    site_configuration.save()

    url = reverse('compile_sass')
    data = {'site_uuid': org.edx_uuid}
    response = client.post(url, data=data,
                           HTTP_X_EDX_API_KEY=settings.EDX_API_KEY)
    content = response.content.decode('utf-8')
    assert response.status_code == status.HTTP_200_OK, content
