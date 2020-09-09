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


class BaseEnrollmentApiTestCase(ModuleStoreTestCase):
    def setUp(self):
        super(BaseEnrollmentApiTestCase, self).setUp()
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

    def call_enrollment_api(self, method, site, caller, req_extra=None):
        req_extra = req_extra or {}
        url = reverse('tahoe-api:v1:enrollments-list')
        method = getattr(APIRequestFactory(), method)
        request = method(url, **req_extra)
        request.META['HTTP_HOST'] = site.domain
        force_authenticate(request, user=caller)

        with mock.patch('lms.djangoapps.instructor.sites.get_current_site', return_value=site):
            with mock.patch('student.models.get_current_site', return_value=site):
                view = resolve(url).func
                response = view(request)
                response.render()
                return response


@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.throttle_classes', [])
class EnrollmentApiGetTest(BaseEnrollmentApiTestCase):
    def test_get_all(self):
        response = self.call_enrollment_api('get', self.my_site, self.caller)
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
        response = self.call_enrollment_api('get', self.my_site, self.caller, {
            'data': {
                'course_id': str(selected_course.id),
            }
        })
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

        response = self.call_enrollment_api('get', self.my_site, self.caller, {
            'data': {
                query_param: str(getattr(user, attr_name)),
            }
        })
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
        co = self.my_course_overviews[0]
        response = self.call_enrollment_api('post', self.my_site, self.caller, {
            'data': {
                'action': 'enroll',
                'auto_enroll': True,
                'identifiers': [],
                'email_learners': True,
                'courses': [
                    str(co.id)
                ],
            }
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_enroll_data_no_courses(self):
        """
        This does a partial test
        """
        response = self.call_enrollment_api('post', self.my_site, self.caller, {
            'data': {
                'action': 'enroll',
                'auto_enroll': True,
                'identifiers': ['alpha@example.com', 'bravo@example.com'],
                'email_learners': True,
                'courses': [],
            }
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@ddt.ddt
@mock.patch(APPSEMBLER_API_VIEWS_MODULE + '.EnrollmentViewSet.throttle_classes', [])
class EnrollmentApiPostTest(BaseEnrollmentApiTestCase):
    def test_enroll_learners_single_course(self):
        """
        The payload structure is subject to change

        TODO: Refactor: Add a test to ensure that the other site does not have
        any new 'CourseEnrollmentAllowed' records
        """
        co = self.my_course_overviews[0]
        reg_users = [UserFactory.create(), UserFactory.create()]

        for reg_user in reg_users:
            # add the users to the site, otherwise they won't have new enrollments
            UserOrganizationMappingFactory(user=reg_user, organization=self.my_site_org)
            # make sure that the registered users are not in the enrollments
            mode, is_active = CourseEnrollment.enrollment_mode_for_user(reg_user, co.id)
            assert mode is None and is_active is None, "email: {}".format(reg_user.email)

        new_users_emails = ['alpha@example.com', 'bravo@example.com']
        # TODO: make sure these emails don't exist
        for new_user_email in new_users_emails:
            assert not CourseEnrollmentAllowed.objects.filter(email=new_user_email).exists()

        before_my_site_ce_count = get_enrollments_for_site(self.my_site).count()
        before_my_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.my_site_org).count()

        before_other_site_ce_count = get_enrollments_for_site(self.other_site).count()
        before_other_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.other_site_org).count()

        payload = {
            'action': 'enroll',
            'auto_enroll': True,
            # Enroll both of the registered users and new ones
            'identifiers': [obj.email for obj in reg_users] + new_users_emails,
            'email_learners': True,
            'courses': [
                str(co.id)
            ],
        }
        response = self.call_enrollment_api('post', self.my_site, self.caller, {
            'data': payload,
        })
        results = response.data['results']
        after_my_site_ce_count = get_enrollments_for_site(self.my_site).count()
        after_my_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.my_site_org).count()

        after_other_site_ce_count = get_enrollments_for_site(self.other_site).count()
        after_other_site_user_count = UserOrganizationMapping.objects.filter(
            organization=self.other_site_org).count()

        assert after_other_site_ce_count == before_other_site_ce_count
        assert after_other_site_user_count == before_other_site_user_count

        assert after_my_site_ce_count == before_my_site_ce_count + len(reg_users)
        assert after_my_site_user_count == before_my_site_user_count

        # By comparing the total count of CourseEnrollmentAllowed records to the
        # number of new users, we verify that CourseEnrollmentAllowed records
        # are not created for the other site. However, this is a hack and brittle.
        # Therefore we want to test this in a more robust way
        assert CourseEnrollmentAllowed.objects.count() == len(new_users_emails)

        for rec in results:
            assert 'error' not in rec
            if rec['identifier'] in new_users_emails:
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

    def test_enroll_learner_in_two_courses(self):
        """
        Enroll a learner in two courses in a single call.
        """
        new_users_email = 'alpha@example.com'
        payload = {
            'action': 'enroll',
            'auto_enroll': True,
            # Enroll both of the registered users and new ones
            'identifiers': [new_users_email],
            'email_learners': True,
            'courses': [str(co.id) for co in self.my_course_overviews],
        }
        response = self.call_enrollment_api('post', self.my_site, self.caller, {
            'data': payload,
        })
        results = response.data['results']
        assert CourseEnrollmentAllowed.objects.count() == len(self.my_course_overviews)
        assert len(results) == len(self.my_course_overviews), 'Ensure result from all courses are returned'

    def test_enroll_with_other_site_course(self):

        reg_users = [UserFactory(), UserFactory()]
        # TODO: Improvement - make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        course_ids = [str(co.id) for co in self.my_course_overviews]
        invalid_course_ids = [str(ce.course.id) for ce in self.other_enrollments]
        course_ids.extend(invalid_course_ids)
        response = self.call_enrollment_api('post', self.my_site, self.caller, {
            'data': {
                'action': 'enroll',
                'auto_enroll': True,
                'identifiers': learner_emails,
                'email_learners': True,
                'courses': course_ids,
            }
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == 'invalid-course-ids'
        assert set(response.data['invalid_course_ids']) == set(invalid_course_ids)

    def test_enroll_with_unsupported_unenroll(self):
        reg_users = [UserFactory(), UserFactory()]
        # TODO: Improvement - make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        course_ids = [str(co.id) for co in self.my_course_overviews]
        response = self.call_enrollment_api('post', self.my_site, self.caller, {
            'data': {
                'action': 'unenroll',
                'auto_enroll': True,
                'identifiers': learner_emails,
                'email_learners': True,
                'courses': course_ids,
            },
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['error'] == 'action-not-supported'
        assert response.data['action_not_supported'] == 'unenroll'

    @ddt.data(None, 'spam', 'delete')
    def test_enroll_with_invalid_action(self, action):
        reg_users = [UserFactory(), UserFactory()]
        # TODO: Improvement - make sure these emails don't exist
        learner_emails = [obj.email for obj in reg_users]
        course_ids = [str(co.id) for co in self.my_course_overviews]
        response = self.call_enrollment_api('post', self.my_site, self.caller, {
            'data': {
                'action': action,
                'auto_enroll': True,
                'identifiers': learner_emails,
                'email_learners': True,
                'courses': course_ids,
            },
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['action'] == [u'"{}" is not a valid choice.'.format(
            'None' if not action else action)]
