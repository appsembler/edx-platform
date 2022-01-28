"""
Tahoe: Unit tests listing the active courses in Studio home.

Ref: RED-2766
"""

from unittest.mock import patch

from django.test import RequestFactory

from contentstore.tests.utils import AjaxEnabledTestClient
from contentstore.views.course import (
    get_courses_accessible_to_user
)
from student.roles import GlobalStaff
from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, check_mongo_calls

from organizations.tests.factories import OrganizationFactory
from organizations.models import OrganizationCourse


from appsembler.waffle import GLOBAL_STAFF_HIDE_INACTIVE_SITES_COURSES


class TestCourseListingGlobalStaffActiveOrgs(ModuleStoreTestCase):
    """
    Tests for the GLOBAL_STAFF_HIDE_INACTIVE_SITES_COURSES Tahoe Waffle Switch.
    """

    def setUp(self):
        """
        Add a user and a course.
        """
        super().setUp()
        self.staff_user = UserFactory.create()
        GlobalStaff().add_users(self.staff_user)
        self.factory = RequestFactory()
        self.request = self.factory.get('/home')
        self.request.user = self.staff_user
        self.client = AjaxEnabledTestClient()
        self.client.login(username=self.staff_user.username, password='test')

        assert GlobalStaff().has_user(self.staff_user), 'Sanity check: verify staff role to the user'

    def _create_course_with_org(self):
        """
        Create dummy course with 'CourseFactory' and link it with a new organization.
        """
        course = CourseFactory.create()
        org = OrganizationFactory.create()
        OrganizationCourse.objects.create(course_id=course.id, organization=org)
        return course, org

    def tearDown(self):
        """
        Reverse the setup
        """
        self.client.logout()
        ModuleStoreTestCase.tearDown(self)

    def test_list_all_active_orgs_when_active_feature_enabled(self):
        """
        TBD.
        """
        active_course_1, active_organization_1 = self._create_course_with_org()
        active_course_2, active_organization_2 = self._create_course_with_org()

        with patch('contentstore.views.course.get_active_organizations') as mocked:
            # List all courses, because all orgs are enabled
            mocked.return_value = [active_organization_1, active_organization_2]
            # Fetch accessible courses list & verify their IDs
            with GLOBAL_STAFF_HIDE_INACTIVE_SITES_COURSES.override(True):
                courses_list_by_staff, __ = get_courses_accessible_to_user(self.request)
                course_ids = set(str(course.id) for course in courses_list_by_staff)
                assert course_ids == {str(active_course_1.id), str(active_course_2.id)}, 'Should list all course'

    # def test_list_active_orgs_when_active_feature_enabled(self):
    #     """
    #     TBD
    #     """
    #     active_course, active_organization = self._create_course_with_org()
    #     _inactive_course, _inactive_organization = self._create_course_with_org()
    #
    #     with patch('contentstore.views.course.get_active_organizations') as mocked:
    #         # list only course from active orgs
    #         mocked.return_value = [active_organization]
    #
    #         # List only courses belonging to active organizations when Tiers enabled
    #         with GLOBAL_STAFF_HIDE_INACTIVE_SITES_COURSES.override(True):
    #             courses_list_by_staff, __ = get_courses_accessible_to_user(self.request)
    #             course_ids = set(str(course.id) for course in courses_list_by_staff)
    #             assert course_ids == {str(active_course.id)}, 'Should list only active courses'
    #
    # def test_list_all_orgs_when_active_feature_disabled(self):
    #     """
    #     TBD
    #     """
    #     active_course, active_organization = self._create_course_with_org()
    #     inactive_course, _inactive_organization = self._create_course_with_org()
    #
    #     with patch('contentstore.views.course.get_active_organizations') as mocked:
    #         # list only course from active orgs
    #         mocked.return_value = [active_organization]
    #
    #         # List all courses the flag is disabled regardless for Tiers output
    #         with GLOBAL_STAFF_HIDE_INACTIVE_SITES_COURSES.override(False):
    #             courses_list_by_staff, __ = get_courses_accessible_to_user(self.request)
    #             course_ids = set(str(course.id) for course in courses_list_by_staff)
    #             assert course_ids == {str(active_course.id),
    #                                   str(inactive_course.id)}, 'Should list all courses, when flag is inactive'
