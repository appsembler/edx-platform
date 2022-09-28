from uuid import UUID

import unittest

from django.db.models import QuerySet
from mock import patch

from django.test import TestCase
from django.test.client import RequestFactory

from openedx.core.djangoapps.appsembler.api.tests.factories import OrganizationFactory
from openedx.core.djangoapps.appsembler.sites.utils import (
    get_active_organizations_uuids,
    get_active_sites,
    get_current_organization,
    get_initial_page_elements,
    get_lms_link_from_course_key,
)
from openedx.core.djangoapps.site_configuration.tests.factories import SiteFactory

from organizations.models import Organization


class JSONMigrationUtilsTestCase(TestCase):
    def test_initial_page_elements(self):
        initial = get_initial_page_elements()

        self.assertEqual(initial['embargo'], {"content": []})

        element = initial['index']['content'][0]['children']['column-1'][0]

        self.assertEqual(element['options']['text-content'], {
            'en': 'Welcome to your Tahoe trial LMS site!',
        })


@patch('openedx.core.djangoapps.appsembler.sites.utils.get_active_site_uuids_from_site_config_service')
@patch('openedx.core.djangoapps.appsembler.sites.utils.get_active_tiers_uuids_from_amc_postgres')
def test_get_active_organizations_uuids(mock_amc_get_uuids, mock_site_config_get_uuids):
    """
    Ensure `get_active_organizations_uuids` reads from both AMC Postgres and Site Config and returns unique results.
    """
    mock_amc_get_uuids.return_value = [
        UUID('aaaaaaaa-1111-0000-1111-dddddddddddd'),
        UUID('aaaaaaaa-2222-0000-2222-dddddddddddd'),
    ]

    mock_site_config_get_uuids.return_value = [
        UUID('aaaaaaaa-2222-0000-2222-dddddddddddd'),  # Duplicates the by mock_amc_get_uuids to test uniqueness
        UUID('aaaaaaaa-5555-0000-5555-dddddddddddd'),
    ]

    assert set(get_active_organizations_uuids()) == {
        UUID('aaaaaaaa-1111-0000-1111-dddddddddddd'),
        UUID('aaaaaaaa-2222-0000-2222-dddddddddddd'),
        UUID('aaaaaaaa-5555-0000-5555-dddddddddddd'),
    }, 'Ensure get_active_organizations_uuids returns unique results'
    assert len(get_active_organizations_uuids()) == 3, (
        'Results should be unique and aaaaaaaa-2222-0000-2222-dddddddddddd should be mentioned only once'
    )


class ActiveSitesTestCase(TestCase):
    def setUp(self):
        super(ActiveSitesTestCase, self).setUp()
        self.siteFoo = SiteFactory.create(domain='foo.dev', name='foo.dev')
        self.siteBar = SiteFactory.create(domain='bar.dev', name='bar.dev')
        self.organizationA = OrganizationFactory(linked_site=self.siteFoo)
        self.organizationB = OrganizationFactory(linked_site=self.siteBar)

    def test_get_active_sites(self):
        """
        Basic test for results.
        """
        with patch('openedx.core.djangoapps.appsembler.sites.utils.get_active_organizations') as mocked:
            mocked.return_value = [self.organizationA, self.organizationB]
            active_sites = get_active_sites()
            assert len(active_sites) == 2
            assert active_sites[0].domain == 'bar.dev'
            assert active_sites[1].domain == 'foo.dev'

    def test_get_active_sites_queryset(self):
        """
        Should return QuerySet to work well with ViewSets and other plugins.
        """
        with patch('openedx.core.djangoapps.appsembler.sites.utils.get_active_organizations') as mocked:
            mocked.return_value = [self.organizationA, self.organizationB]
            active_sites = get_active_sites()
            assert type(active_sites) == QuerySet

    def test_get_active_sites_ordering(self):
        """
        Result ordering is useful for tests but it's worth testing it itself.
        """
        with patch('openedx.core.djangoapps.appsembler.sites.utils.get_active_organizations') as mocked:
            mocked.return_value = [self.organizationA, self.organizationB]
            active_sites = get_active_sites('-domain')
            assert active_sites[0].domain == 'foo.dev'


class OrganizationByRequestTestCase(TestCase):
    def setUp(self):
        super(OrganizationByRequestTestCase, self).setUp()
        self.siteBaz = SiteFactory.create(domain='baz.dev', name='baz.dev')
        self.request = RequestFactory().post('dummy_url')
        self.request.session = {}
        for patch_req in (
            'openedx.core.djangoapps.appsembler.sites.utils.get_current_request',
            'openedx.core.djangoapps.theming.helpers.get_current_request',
        ):
            patcher = patch(patch_req)
            patched_req = patcher.start()
            patched_req.return_value = self.request
            self.addCleanup(patcher.stop)

    @unittest.skip
    def test_amc_admin_user_no_org_in_request(self):
        # TODO: would be good to test
        pass

    def test_no_org_for_site(self):
        self.request.site = self.siteBaz
        with self.assertRaises(Organization.DoesNotExist):
            get_current_organization()


class LMSLinkByCourseOrgTestCase(TestCase):
    """
    Exercise getting the appropriate LMS Link for Studio "View in LMS"
    based on the organization value set on the course that is being viewed.
    (note we don't test with custom domains since that is handled by middleware)
    """
    def setUp(self):
        super(LMSLinkByCourseOrgTestCase, self).setUp()
        self.siteFoo = SiteFactory.create(domain='foo.dev', name='foo.dev')
        self.courseKey = "course-v1:org+course+run"
        self.base_lms_url = "lms_base.domain"

    @patch('openedx.core.djangoapps.appsembler.api.sites.get_site_for_course')
    def test_lms_link_happy_path(self, mocked_get_site_for_course):
        mocked_get_site_for_course.return_value = self.siteFoo
        url = get_lms_link_from_course_key(self.base_lms_url, self.courseKey)
        self.assertEqual(url, "foo.dev")

    @patch('openedx.core.djangoapps.appsembler.api.sites.get_site_for_course')
    def test_lms_link_no_site_matching_course(self, mocked_get_site_for_course):
        mocked_get_site_for_course.return_value = None
        url = get_lms_link_from_course_key(self.base_lms_url, self.courseKey)
        self.assertEqual(url, self.base_lms_url)

    @patch.dict('django.conf.settings.FEATURES', {
        'PREVIEW_LMS_BASE': 'preview.lms_base.domain'
    })
    def test_lms_link_for_preview_always_return_preview_domain(self):
        preview_url = "preview.lms_base.domain"
        url = get_lms_link_from_course_key(preview_url, self.courseKey)
        self.assertEqual(url, preview_url)
