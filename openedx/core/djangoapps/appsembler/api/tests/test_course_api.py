"""
Tests for openedx.core.djangoapps.appsembler.api.v1.views.CourseViewSet

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

from openedx.core.djangoapps.appsembler.api.tests.factories import (
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
    UserOrganizationMappingFactory,
)


APPSEMBLER_API_VIEWS_MODULE = 'openedx.core.djangoapps.appsembler.api.v1.views'


@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CourseViewSet.authentication_classes', [])
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CourseViewSet.permission_classes', [AllowAny])
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.CourseViewSet.throttle_classes', [])
class CourseApiTest(TestCase):

    def setUp(self):
        self.my_site = Site.objects.get(domain=u'example.com')
        self.other_site = SiteFactory(domain='other-site.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])

        self.my_course_overviews = [
            CourseOverviewFactory(),
            CourseOverviewFactory()
        ]
        for co in self.my_course_overviews:
            OrganizationCourseFactory(organization=self.my_site_org,
                                      course_id=str(co.id))

        self.other_course_overviews = [CourseOverviewFactory()]
        OrganizationCourseFactory(organization=self.other_site_org,
                                  course_id=str(self.other_course_overviews[0].id))

    def test_get_list(self):
        url = reverse('tahoe-api:v1:courses-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        course_list = res.data['results']
        expected_keys = [str(co.id) for co in self.my_course_overviews]
        self.assertEqual(set([obj['id'] for obj in course_list]), set(expected_keys) )

    def test_get_single(self):
        course_id = str(self.my_course_overviews[0].id)
        url = reverse('tahoe-api:v1:courses-detail', args=[course_id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['id'], course_id) 
