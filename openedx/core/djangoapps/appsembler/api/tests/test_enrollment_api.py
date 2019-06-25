"""
Tests for openedx.core.djangoapps.appsembler.api.views.EnrollmentViewSet

These tests adapted from Appsembler enterprise `appsembler_api` tests

"""
from django.contrib.sites.models import Site
from django.core.urlresolvers import resolve, reverse
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory, force_authenticate

import ddt
import mock
from unittest import skip

from openedx.core.djangoapps.site_configuration.tests.factories import (
    SiteConfigurationFactory,
    SiteFactory,
)

from student.models import CourseEnrollment
from student.tests.factories import CourseEnrollmentFactory, UserFactory

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.django import modulestore

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
class EnrollmentApiTest(ModuleStoreTestCase):

    def setUp(self):
        super(EnrollmentApiTest, self).setUp()
        # store = modulestore()
        self.my_site = Site.objects.get(domain=u'example.com')
        self.other_site = SiteFactory(domain='other-site.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])

        self.my_courses = [CourseFactory.create() for i in range(0,2)]
        self.my_course_overviews = [
            CourseOverviewFactory(id=course.id) for course in self.my_courses
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
        enroll_list = res.data['results']
        self.assertEqual(len(enroll_list), len(self.my_enrollments))
        # TODO: Validate each record

    def test_get_enrollments_for_course(self):
        selected_course = self.my_course_overviews[0]
        expected_enrollments = [
            CourseEnrollmentFactory(course=selected_course),
            CourseEnrollmentFactory(course=selected_course),
        ]

        for enrollment in expected_enrollments:
            UserOrganizationMappingFactory(user=enrollment.user,
                                           organization=self.my_site_org)
        expected_enrollments.append(self.my_enrollments[0])
        url = reverse('tahoe-api:v1:enrollments-list')
        url += '?course_id={}'.format(str(selected_course.id))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        enroll_list = res.data['results']
        self.assertEqual(len(enroll_list), len(expected_enrollments))
        # TODO: Validate each record

    def test_get_single_enrollment(self):
        pass


    def test_invalid_enroll_data_no_learners(self):
        """
        This does a partial test
        """
        url = reverse('tahoe-api:v1:enrollments-list')
        co = self.my_course_overviews[0]
        payload = {
            'action': 'enroll',
            'auto_enroll': True,
            'identifiers': [],
            'email_learners': True,
            'courses': [
                str(co.id)
            ],
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_enroll_data_no_courses(self):
        """
        This does a partial test
        """
        url = reverse('tahoe-api:v1:enrollments-list')
        co = self.my_course_overviews[0]
        payload = {
            'action': 'enroll',
            'auto_enroll': True,
            'identifiers': ['alpha@example.com', 'bravo@example.com'],
            'email_learners': True,
            'courses': [],
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @skip('needs user')
    def test_enroll_learners_single_course(self):
        """
        The payload structure is subject to change
        """
        url = reverse('tahoe-api:v1:enrollments-list')
        co = self.my_course_overviews[0]
        reg_users = [UserFactory(), UserFactory()]
        new_users = ['alpha@example.com', 'bravo@example.com']
        # TODO: make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        payload = {
            'action': 'enroll',
            'auto_enroll': True,
            'identifiers': learner_emails,
            'email_learners': True,
            'courses': [
                str(co.id)
            ],
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in ['action', 'auto_enroll', 'email_learners', 'courses']:
            self.assertEqual(res.data[key], payload[key])

        # TODO: Assert that the course enrollments created
        # TODO: Assert new users registered
        import pdb; pdb.set_trace()


@ddt.ddt
# @mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.authentication_classes', [])
# @mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.permission_classes', [AllowAny])
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.throttle_classes', [])
class EnrollmentApiPostTest(ModuleStoreTestCase):

    def setUp(self):
        super(EnrollmentApiPostTest, self).setUp()
        # store = modulestore()
        self.my_site = Site.objects.get(domain=u'example.com')
        self.other_site = SiteFactory(domain='other-site.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])

        self.my_courses = [CourseFactory.create() for i in range(0,2)]
        self.my_course_overviews = [
            CourseOverviewFactory(id=course.id) for course in self.my_courses
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

        self.caller = UserFactory()
        UserOrganizationMappingFactory(user=self.caller,
                                organization=self.my_site_org,
                                is_amc_admin=True,
            )


    def test_enroll_learners_single_course(self):
        """
        The payload structure is subject to change
        """

        co = self.my_course_overviews[0]
        reg_users = [UserFactory(), UserFactory()]
        new_users = ['alpha@example.com', 'bravo@example.com']
        # TODO: make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        payload = {
            'action': 'enroll',
            'auto_enroll': True,
            'identifiers': learner_emails,
            'email_learners': True,
            'courses': [
                str(co.id)
            ],
        }


        factory = APIRequestFactory()
        url = reverse('tahoe-api:v1:enrollments-list') 
        request = factory.post(url, payload)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)

        view = resolve(url).func
        response = view(request)
        response.render()

        import pdb; pdb.set_trace()


        # res = self.client.post(url, payload)
        # self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # for key in ['action', 'auto_enroll', 'email_learners', 'courses']:
        #     self.assertEqual(res.data[key], payload[key])

        # # TODO: Assert that the course enrollments created
        # # TODO: Assert new users registered
        # import pdb; pdb.set_trace()
