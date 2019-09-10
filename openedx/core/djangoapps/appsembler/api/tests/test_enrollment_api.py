"""
Tests for openedx.core.djangoapps.appsembler.api.views.EnrollmentViewSet

These tests adapted from Appsembler enterprise `appsembler_api` tests

"""
# from django.contrib.sites.models import Site
from django.core.urlresolvers import resolve, reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

import ddt
import mock

from openedx.core.djangoapps.site_configuration.tests.factories import (
    SiteFactory,
)

from student.models import CourseEnrollment, CourseEnrollmentAllowed
from student.tests.factories import CourseEnrollmentFactory, UserFactory

from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

from organizations.models import UserOrganizationMapping
from openedx.core.djangoapps.appsembler.api.sites import (
    get_enrollments_for_site,
)

from openedx.core.djangoapps.appsembler.api.tests.factories import (
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
    UserOrganizationMappingFactory,
)


APPSEMBLER_API_VIEWS_MODULE = 'openedx.core.djangoapps.appsembler.api.v1.views'


@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.throttle_classes', [])
class EnrollmentApiGetTest(ModuleStoreTestCase):

    def setUp(self):
        super(EnrollmentApiGetTest, self).setUp()
        self.my_site = SiteFactory(domain='my-site.test')
        self.other_site = SiteFactory(domain='other-site.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])

        self.my_courses = [CourseFactory.create() for i in range(0, 2)]
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

    def test_get_all(self):
        url = reverse('tahoe-api:v1:enrollments-list')
        request = APIRequestFactory().get(url)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)

        view = resolve(url).func
        response = view(request)
        response.render()
        results = response.data['results']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(results), len(self.my_enrollments))
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

        # Need to resolve without the query parameters
        view = resolve(url).func
        url += '?course_id={}'.format(str(selected_course.id))
        request = APIRequestFactory().get(url)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        response = view(request)
        response.render()
        results = response.data['results']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(results), len(expected_enrollments))
        # TODO: Validate each record

    def test_get_single_enrollment(self):
        pass

    @ddt.data(('user_id', 'id'), ('username', 'username'))
    @ddt.unpack
    def test_get_enrollments_for_user(self, query_param, attr_name):
        # Set up additional test data
        user = UserFactory()
        UserOrganizationMappingFactory(user=self.caller,
                                       organization=self.my_site_org,
                                       is_amc_admin=True)
        courses = [CourseFactory.create() for i in range(0, 3)]
        course_overviews = []
        course_enrollments = []
        for course in courses:
            OrganizationCourseFactory(organization=self.my_site_org,
                                      course_id=str(course.id))
            course_overview = CourseOverviewFactory(id=course.id)
            course_enrollment = CourseEnrollmentFactory(course=course_overview,
                                                        user=user)
            course_overviews.append(course_overview)
            course_enrollments.append(course_enrollment)

        # Set up our request
        url = reverse('tahoe-api:v1:enrollments-list')
        # Need to resolve without the query parameters
        view = resolve(url).func
        url += '?{}={}'.format(query_param, getattr(user, attr_name))
        request = APIRequestFactory().get(url)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        response = view(request)
        response.render()
        results = response.data['results']

        expected_course_ids = [str(co.id) for co in course_overviews]
        found_course_ids = [obj['course_details']['course_id'] for obj in results]
        assert set(found_course_ids) == set(expected_course_ids)
        for result in results:
            assert result['user'] == user.username

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

        request = APIRequestFactory().post(url, payload)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        view = resolve(url).func
        response = view(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_enroll_data_no_courses(self):
        """
        This does a partial test
        """
        url = reverse('tahoe-api:v1:enrollments-list')
        payload = {
            'action': 'enroll',
            'auto_enroll': True,
            'identifiers': ['alpha@example.com', 'bravo@example.com'],
            'email_learners': True,
            'courses': [],
        }
        request = APIRequestFactory().post(url, payload)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        view = resolve(url).func
        response = view(request)
        response.render()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

REQUEST_CACHE_CLASS = 'openedx.core.djangoapps.request_cache.middleware.RequestCache'

# class MockRequestCache(object):
#    @classmethod
#    def get_current_request(cls):
#        return 

@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.throttle_classes', [])
# @mock.patch(REQUEST_CACHE_CLASS, MockRequestCache)
class EnrollmentApiPostTest(ModuleStoreTestCase):

    def setUp(self):
        super(EnrollmentApiPostTest, self).setUp()
        self.my_site = SiteFactory(domain='my-site.test')
        self.other_site = SiteFactory(domain='other-site.test')
        self.other_site_org = OrganizationFactory(sites=[self.other_site])
        self.my_site_org = OrganizationFactory(sites=[self.my_site])

        self.my_courses = [CourseFactory.create() for i in range(0, 2)]
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

        TODO: Refactor: Add a test to ensure that the other site does not have
        any new 'CourseEnrollmentAllowed' records
        """
        co = self.my_course_overviews[0]
        reg_users = [UserFactory(), UserFactory()]

        # make sure that the registered users are not in the enrollments
        for user in reg_users:
            mode, is_active = CourseEnrollment.enrollment_mode_for_user(user, co.id)
            assert mode is None and is_active is None, "email: {}".format(user.email)

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

        for user_email in new_users:
            assert not CourseEnrollmentAllowed.objects.filter(email=user_email).exists()

        url = reverse('tahoe-api:v1:enrollments-list')
        request = APIRequestFactory().post(url, payload)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)
        before_my_site_ce_count = get_enrollments_for_site(self.my_site).count()
        before_my_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.my_site_org).count()

        before_other_site_ce_count = get_enrollments_for_site(self.other_site).count()
        before_other_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.other_site_org).count()

        view = resolve(url).func
        INSTRUCTOR_SITES = 'lms.djangoapps.instructor.sites'
        def mock_get_current_site():
            return self.my_site


        with mock.patch(INSTRUCTOR_SITES + '.get_current_site', mock_get_current_site): 
            response = view(request)
            response.render()

            results = response.data['results']
            after_my_site_ce_count = get_enrollments_for_site(self.my_site).count()
            after_my_site_user_count = UserOrganizationMapping.objects.filter(
                organization=self.my_site_org).count()

            after_other_site_ce_count = get_enrollments_for_site(self.other_site).count()
            after_other_site_user_count = UserOrganizationMapping.objects.filter(
                organization=self.other_site_org).count()

            assert after_other_site_ce_count == before_other_site_ce_count
            assert after_other_site_user_count == before_other_site_user_count

            import pdb; pdb.set_trace()
            assert after_my_site_ce_count == before_my_site_ce_count + len(reg_users)
            assert after_my_site_user_count == before_my_site_user_count

            # By comparing the total count of CourseEnrollmentAllowed records to the
            # number of new users, we verify that CourseEnrollmentAllowed records
            # are not created for the other site. However, this is a hack and brittle.
            # Therefore we want to test this in a more robust way
            assert CourseEnrollmentAllowed.objects.count() == len(new_users)

            for rec in results:
                assert 'error' not in rec
                if rec['identifier'] in new_users:
                    assert CourseEnrollmentAllowed.objects.filter(
                        email=rec['identifier']).exists()

                    assert rec['before'] == dict(enrollment=False,
                                                 auto_enroll=False,
                                                 user=False,
                                                 allowed=False)
                    assert rec['after'] == dict(enrollment=False,
                                                auto_enroll=payload['auto_enroll'],
                                                user=False,
                                                allowed=True)
                else:
                    assert rec['before'] == dict(enrollment=False,
                                                 auto_enroll=False,
                                                 user=True,
                                                 allowed=False)
                    assert rec['after'] == dict(enrollment=True,
                                                auto_enroll=False,
                                                user=True,
                                                allowed=False)
                    assert not CourseEnrollmentAllowed.objects.filter(
                        email=rec['identifier']).exists()

    def test_enroll_with_other_site_course(self):

        reg_users = [UserFactory(), UserFactory()]
        # TODO: Improvement - make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        course_ids = [str(co.id) for co in self.my_course_overviews]
        invalid_course_ids = [str(ce.course.id) for ce in self.other_enrollments]
        course_ids.extend(invalid_course_ids)
        payload = {
            'action': 'enroll',
            'auto_enroll': True,
            'identifiers': learner_emails,
            'email_learners': True,
            'courses': course_ids,
        }

        url = reverse('tahoe-api:v1:enrollments-list')
        request = APIRequestFactory().post(url, payload)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)

        view = resolve(url).func
        response = view(request)
        response.render()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == 'invalid-course-ids'
        assert set(response.data['invalid_course_ids']) == set(invalid_course_ids)

    def test_enroll_with_unsupported_unenroll(self):
        reg_users = [UserFactory(), UserFactory()]
        # TODO: Improvement - make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        course_ids = [str(co.id) for co in self.my_course_overviews]
        payload = {
            'action': 'unenroll',
            'auto_enroll': True,
            'identifiers': learner_emails,
            'email_learners': True,
            'courses': course_ids,
        }

        url = reverse('tahoe-api:v1:enrollments-list')
        request = APIRequestFactory().post(url, payload)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)

        view = resolve(url).func
        response = view(request)
        response.render()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == 'action-not-supported'
        assert response.data['action_not_supported'] == 'unenroll'

    @ddt.data(None, 'spam', 'delete')
    def test_enroll_with_invalid_action(self, action):
        reg_users = [UserFactory(), UserFactory()]
        # TODO: Improvement - make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        course_ids = [str(co.id) for co in self.my_course_overviews]
        payload = {
            'action': action,
            'auto_enroll': True,
            'identifiers': learner_emails,
            'email_learners': True,
            'courses': course_ids,
        }

        url = reverse('tahoe-api:v1:enrollments-list')
        request = APIRequestFactory().post(url, payload)
        request.META['HTTP_HOST'] = self.my_site.domain
        force_authenticate(request, user=self.caller)

        view = resolve(url).func
        response = view(request)
        response.render()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['action'] == [u'"{}" is not a valid choice.'.format(
            'None' if not action else action)]
