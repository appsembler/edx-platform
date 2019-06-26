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

from student.models import CourseEnrollment, CourseEnrollmentAllowed
from student.tests.factories import CourseEnrollmentFactory, UserFactory

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from xmodule.modulestore.django import modulestore

from organizations.models import UserOrganizationMapping
from openedx.core.djangoapps.appsembler.api.sites import (
    get_courses_for_site,
    get_site_for_course,
    get_enrollments_for_site,
)

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
class EnrollmentApiGetTest(ModuleStoreTestCase):

    def setUp(self):
        super(EnrollmentApiGetTest, self).setUp()
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


@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.throttle_classes', [])
class EnrollmentApiPostTest(ModuleStoreTestCase):

    def setUp(self):
        super(EnrollmentApiPostTest, self).setUp()
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
        OrganizationCourseFactory(organization=self.other_site_org,
                                  course_id=str(
                                    self.other_enrollments[0].course_overview.id))

        self.caller = UserFactory()
        UserOrganizationMappingFactory(user=self.caller,
                                       organization=self.my_site_org,
                                       is_amc_admin=True)

    def test_enroll_learners_single_course(self):
        """
        The payload structure is subject to change
        """

        co = self.my_course_overviews[0]
        reg_users = [UserFactory(), UserFactory()]
        new_users = ['alpha@example.com', 'bravo@example.com']
        # TODO: make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        learner_emails.extend(new_users)
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

        other_site_ce = get_enrollments_for_site(self.other_site)
        other_site_ce_count = other_site_ce.count()

        before_my_site_ce_count = get_enrollments_for_site(self.my_site).count()
        before_my_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.my_site_org).count()

        before_other_site_ce_count = get_enrollments_for_site(self.other_site).count()
        before_other_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.other_site_org).count()

        view = resolve(url).func
        response = view(request)
        response.render()
        # existing course enrollments for site

        results = response.data['results']
        new_ce_count = len(results)
        after_my_site_ce_count = get_enrollments_for_site(self.my_site).count()
        after_my_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.my_site_org).count()

        after_other_site_ce_count = get_enrollments_for_site(self.other_site).count()
        after_other_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.other_site_org).count()

        assert after_other_site_ce_count == before_other_site_ce_count
        assert after_other_site_user_count == before_other_site_user_count

        assert after_my_site_ce_count == before_my_site_ce_count
        assert after_my_site_user_count == before_my_site_user_count
        assert CourseEnrollmentAllowed.objects.count() == len(new_users)

        # Sample data to make sure we're testing
        # {'identifier': u'alpha@example.com',
        # 'after': {'enrollment': False, 'auto_enroll': True, 'user': False, 'allowed': True},
        # 'before': {'enrollment': False, 'auto_enroll': False, 'user': False, 'allowed': False}}

        # {'identifier': u'robot+test+22@edx.org',
        # 'after': {'enrollment': True, 'auto_enroll': False, 'user': True, 'allowed': False},
        # 'before': {'enrollment': False, 'auto_enroll': False, 'user': True, 'allowed': False}}

        # TODO: check each enrollment
        for rec in results:
            assert not rec.has_key('error')
            assert rec['before']['auto_enroll'] == payload['auto_enroll']
            assert rec['after']['auto_enroll'] == payload['auto_enroll']
            if rec['identifier'] in new_users:
                assert CourseEnrollmentAllowed.objects.filter(
                    email=rec['identifier']).count() == 1

                assert rec['before'] == dict(enrollment=False,
                                             auto_enroll=payload['auto_enroll'],
                                             user=False,
                                             allowed=False)
                assert rec['after'] == dict(enrollment=False,
                                            auto_enroll=payload['auto_enroll'],
                                            user=False,
                                            allowed=True)
                # before = rec['before']
                # assert before['enrollment'] == False
                # assert before['user'] == False
                # assert before['allowed'] == False
                # after = rec['after']
                # assert after['enrollment'] == False
                # assert after['user'] == False
                # assert after['allowed'] == True
            # else:
            #     assert  rec['']
            #     assert rec['before']['allowed'] == False
            #     assert rec['after']['allowed'] == True



        # import pdb; pdb.set_trace()



