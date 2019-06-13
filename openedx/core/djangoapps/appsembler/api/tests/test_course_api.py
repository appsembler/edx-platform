"""
Tests for openedx.core.djangoapps.appsembler.api.views.RegistrationViewSet

These tests adapted from Appsembler enterprise `appsembler_api` tests

"""

from django.contrib.sites.models import Site
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
    OrganizationCourseFactory,
    UserOrganizationMappingFactory,
)


SITE_CONFIGURATION_CLASS = ('openedx.core.djangoapps.site_configuration'
                            '.models.SiteConfiguration')

APPSEMBLER_API_VIEWS_MODULE = 'openedx.core.djangoapps.appsembler.api.v1.views'


# The mock.patch breaks the test. Causes 

@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CourseViewSet.authentication_classes', [])
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CourseViewSet.permission_classes', [AllowAny])
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CourseViewSet.throttle_classes', [])
class CourseApiTest(TestCase):

    def setUp(self):
        self.other_site = Site.objects.get(domain=u'example.com')
        self.my_site = SiteFactory(domain='foo.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])

        # THIS BREAKS! (We might not need it)
        # self.site_configuration = SiteConfigurationFactory(
        #     site=self.site,
        #     sass_variables={},
        #     page_elements={},
        # )

        self.my_course_overviews = [
            CourseOverviewFactory(),
            CourseOverviewFactory()
        ]
        OrganizationCourseFactory(organization=self.my_site_org,
                                  course_id=str(self.my_course_overviews[0].id))
        OrganizationCourseFactory(organization=self.my_site_org,
                                  course_id=str(self.my_course_overviews[1].id))

        self.other_course_overviews = [CourseOverviewFactory()]
        OrganizationCourseFactory(organization=self.other_site_org,
                                  course_id=str(self.other_course_overviews[0].id))

    def test_get_list(self):
        list_url = reverse('tahoe-api:v1:courses-list')
        res = self.client.get(list_url)
        self.assertEqual(res.status_code, 200)

        course_list = res.json().get('results')

        # Breaks. only one course id is returned
        self.assertEqual(len(course_list), len(self.my_course_overviews))

        # TODO: Convert results to CourseKey or string and compare to my_course_overviews
