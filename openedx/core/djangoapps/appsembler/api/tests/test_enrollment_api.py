"""
Tests for openedx.core.djangoapps.appsembler.api.views.EnrollmentViewSet

These tests adapted from Appsembler enterprise `appsembler_api` tests

"""
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.permissions import AllowAny

import ddt
import mock

from openedx.core.djangoapps.site_configuration.tests.factories import (
    SiteConfigurationFactory,
    SiteFactory,
)

from student.models import CourseEnrollment
from student.tests.factories import CourseEnrollmentFactory, UserFactory

from .factories import (
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
    UserOrganizationMappingFactory,
)


APPSEMBLER_API_VIEWS_MODULE = 'openedx.core.djangoapps.appsembler.api.v1.views'


@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.authentication_classes', [])
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.permission_classes', [AllowAny])
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.throttle_classes', [])
class EnrollmentApiTest(TestCase):
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

        self.my_enrollments = [
            CourseEnrollmentFactory(course=self.my_course_overviews[0]),
            CourseEnrollmentFactory(course=self.my_course_overviews[1]),
        ]

        for enrollment in self.my_enrollments:
            UserOrganizationMappingFactory(user=enrollment.user,
                                           organization=self.my_site_org)

        self.other_enrollments = [CourseEnrollmentFactory()]
        # self.other_course_overviews = [CourseOverviewFactory()]
        OrganizationCourseFactory(organization=self.other_site_org,
                                  course_id=str(
                                    self.other_enrollments[0].course_overview.id))

    def test_get_all(self):
        url = reverse('tahoe-api:v1:enrollments-list')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        enrollments_list = res.data['results']
        self.assertEqual(len(enrollments_list))
        import pdb; pdb.set_trace()


    def test_get_single(self):


# @ddt.ddt
# @patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.authentication_classes', [])
# @patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.permission_classes', [AllowAny])
# @patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.throttle_classes', [])
# class EnrollmentApiPostTest(TestCase):
#     def setUp(self):

#     def test_enroll_registered_user(self):
#         # The DRF Router appends '-list' to the base 'registrations' name when
#         # registering the endpoint

#         url = reverse('tahoe-api:v1:enrollments')
#         payload = {
#             'email': 'mr.robot@example.com',
#             'course_id':
#         }
#         res = self.client.post(url, payload)
#         self.assertEqual(res.status_code, 200)
#         course_list = res.data['results']
#         expected_keys = [str(co.id) for co in self.my_course_overviews]
#         self.assertEqual(set([obj['id'] for obj in course_list]), set(expected_keys) )
