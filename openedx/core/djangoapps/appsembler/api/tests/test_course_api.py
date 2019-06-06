"""
Tests for openedx.core.djangoapps.appsembler.api.views.RegistrationViewSet

These tests adapted from Appsembler enterprise `appsembler_api` tests

"""
from django.core.urlresolvers import reverse
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from rest_framework.permissions import AllowAny

import ddt
import mock


from student.tests.factories import UserFactory
from openedx.core.djangoapps.site_configuration.tests.factories import (
    SiteConfigurationFactory,
    SiteFactory,
)

from .factories import (
    CourseOverviewFactory,
    OrganizationFactory,
    UserOrganizationMappingFactory,
)


SITE_CONFIGURATION_CLASS = ('openedx.core.djangoapps.site_configuration'
                            '.models.SiteConfiguration')

APPSEMBLER_API_VIEWS_MODULE = 'openedx.core.djangoapps.appsembler.api.v1.views'


@ddt.ddt
class SiteAdminPermissionsTest(TestCase):

    def setUp(self):
        patch = mock.patch(SITE_CONFIGURATION_CLASS + '.compile_microsite_sass')
        self.mock_site_config_method = patch.start()
        self.site = SiteFactory()
        self.organization = OrganizationFactory(
            sites=[self.site],
        )
        self.site_configuration = SiteConfigurationFactory(
            site=self.site,
            sass_variables={},
            page_elements={},
        )
        self.site_configuration.values['course_org_filter'] = self.organization.short_name
        self.callers = [
            UserFactory(username='alpha_nonadmin'),
            UserFactory(username='alpha_site_admin'),
            UserFactory(username='non_site_user'),
        ]
        self.user_organization_mappings = [
            UserOrganizationMappingFactory(
                user=self.callers[0], organization=self.organization),
            UserOrganizationMappingFactory(
                user=self
                .callers[1], organization=self.organization, is_amc_admin=True),
            # Make sure we DO NOT add the 'non_site_user' here
        ]
        # self.factory = RequestFactory()
        self.addCleanup(patch.stop)

    def test_get_list(self):
        list_url = reverse('tahoe-api:v1:courses-list')
        res = self.client.get(list_url)
        
        import pdb; pdb.set_trace()


# @ddt.ddt
# @mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CoursesViewSet.authentication_classes', [])
# @mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CourseViewSet.permission_classes', [AllowAny])
# @mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CourseViewSet.throttle_classes', [])
# @mock.patch(SITE_CONFIGURATION_CLASS + '.compile_microsite_sass')
# @override_settings(APPSEMBLER_FEATURES={
#     'SKIP_LOGIN_AFTER_REGISTRATION': False,
# })
# class CourseApiViewTests(TestCase):
#     def setUp(self):

#         # The DRF Router appends '-list' to the base 'registrations' name when
#         # registering the endpoint

#         self.site = SiteFactory()
#         self.organization = OrganizationFactory(
#             sites=[self.site],
#         )
#         self.site_configuration = SiteConfigurationFactory(
#             site=self.site,
#             sass_variables={},
#             page_elements={},
#         )
#         self.site_configuration.values['course_org_filter'] = self.organization.short_name
#         self.callers = [
#             UserFactory(username='alpha_nonadmin'),
#             UserFactory(username='alpha_site_admin'),
#             UserFactory(username='non_site_user'),
#         ]
#         self.user_organization_mappings = [
#             UserOrganizationMappingFactory(
#                 user=self.callers[0], organization=self.organization),
#             UserOrganizationMappingFactory(
#                 user=self
#                 .callers[1], organization=self.organization, is_amc_admin=True),
#             # Make sure we DO NOT add the 'non_site_user' here
#         ]






# BORKEN - 

# @ddt.ddt
# @mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.RegistrationViewSet.authentication_classes', [])
# @mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.RegistrationViewSet.permission_classes', [AllowAny])
# @mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.RegistrationViewSet.throttle_classes', [])
# @override_settings(APPSEMBLER_FEATURES={
#     'SKIP_LOGIN_AFTER_REGISTRATION': False,
# })
# class CourseApiViewTests(TestCase):
#     def setUp(self):

#         # The DRF Router appends '-list' to the base 'registrations' name when
#         # registering the endpoint
#         self.url = reverse('tahoe-api:v1:courses-list')
#         patch = mock.patch(SITE_CONFIGURATION_CLASS + '.compile_microsite_sass')
#         self.mock_site_config_method = patch.start()
#         self.site = SiteFactory()
#         self.organization = OrganizationFactory(
#             sites=[self.site],
#         )
#         self.site_configuration = SiteConfigurationFactory(
#             site=self.site,
#             sass_variables={},
#             page_elements={},
#         )
#         self.site_configuration.values['course_org_filter'] = self.organization.short_name
#         self.callers = [
#             UserFactory(username='alpha_nonadmin'),
#             UserFactory(username='alpha_site_admin'),
#             UserFactory(username='non_site_user'),
#         ]
#         self.user_organization_mappings = [
#             UserOrganizationMappingFactory(
#                 user=self.callers[0], organization=self.organization),
#             UserOrganizationMappingFactory(
#                 user=self
#                 .callers[1], organization=self.organization, is_amc_admin=True),
#             # Make sure we DO NOT add the 'non_site_user' here
#         ]
#         # self.factory = RequestFactory()

#         self.addCleanup(patch.stop)

#     def test_get_list(self):

#         res = self.client.get(self.url)
        
#         import pdb; pdb.set_trace()





