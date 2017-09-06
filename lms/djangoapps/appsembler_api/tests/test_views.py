"""
Tests for the Appsembler API views.
"""
from urllib import quote

from django.core.urlresolvers import reverse
from mock import patch
from rest_framework import status
import json
import ddt
from rest_framework.permissions import AllowAny
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory

from student.roles import REGISTERED_ACCESS_ROLES, CourseRole, CourseStaffRole, CourseInstructorRole
from student.tests.factories import UserFactory
from appsembler_api.views import CourseRolesView


@ddt.ddt
@patch.object(CourseRolesView, 'permission_classes', [AllowAny])  # Skip authentication for tests
class CourseRolesViewTestCase(SharedModuleStoreTestCase):
    COURSE_ROLES = [
        role_class for role_class in REGISTERED_ACCESS_ROLES.values()
        if issubclass(role_class, CourseRole)
    ]

    @classmethod
    def setUpClass(cls):
        """
        Course is created here and shared by all the class's tests.
        """
        super(CourseRolesViewTestCase, cls).setUpClass()
        cls.course = CourseFactory.create()

    def setUp(self):
        super(CourseRolesViewTestCase, self).setUp()
        self.api_url = reverse('course_roles_api', args=[unicode(self.course.id)])

    @ddt.data(*COURSE_ROLES)
    def test_ensure_empty_roles(self, role_class):
        users = role_class(self.course.id).users_with_role()
        self.assertFalse(users)  # Course should not have anyone in the roles by default

    @ddt.data(*COURSE_ROLES)
    def test_empty_roles(self, role_class):
        res = self.client.get(self.api_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        roles = res.data['roles']
        self.assertFalse(roles[role_class.ROLE])  # The API should provide no roles when there isn't any

    def test_basic_get(self):
        staff_1 = UserFactory.create()
        staff_2 = UserFactory.create()
        instructor = UserFactory.create()

        CourseInstructorRole(self.course.id).add_users(instructor)
        CourseStaffRole(self.course.id).add_users(staff_1)
        CourseStaffRole(self.course.id).add_users(staff_2)

        res = self.client.get(self.api_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        roles = res.data['roles']

        self.assertEqual(len(roles['instructor']), 1)  # Should have one instructor
        self.assertEqual(len(roles['staff']), 2)  # Should have two staff

        self.assertEqual(instructor.username, roles['instructor'][0]['username'])

        staff_usernames = [user['username'] for user in roles['staff']]
        self.assertIn(staff_1.username, staff_usernames)
        self.assertIn(staff_2.username, staff_usernames)

    def test_basic_put(self):
        staff = UserFactory.create()
        instructor_1 = UserFactory.create()
        instructor_2 = UserFactory.create()

        instructor_role = CourseInstructorRole(self.course.id)
        staff_role = CourseStaffRole(self.course.id)

        res = self.client.put(self.api_url, content_type='application/json', data=json.dumps({
            'roles': {
                'staff': [
                    staff.username,
                ],
                'instructor': [
                    instructor_1.username,
                    instructor_2.email,
                ],
            },
        }))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertTrue(staff_role.has_user(staff), 'Should be staff')
        self.assertTrue(instructor_role.has_user(instructor_1), 'Should be instructor')
        self.assertTrue(instructor_role.has_user(instructor_2), 'Should be instructor')

    def test_delete(self):
        instructor = UserFactory.create()
        staff = UserFactory.create()

        instructor_role = CourseInstructorRole(self.course.id)
        staff_role = CourseStaffRole(self.course.id)

        instructor_role.add_users(instructor)
        staff_role.add_users(staff)

        roles_to_delete = quote(json.dumps({
            'staff': [staff.username],
        }))

        def assert_proper_deletion(res):
            """
            Make sure deletion is properly implemented and idempotent.
            """
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertTrue(instructor_role.has_user(instructor), 'Should stay as instructor')
            self.assertFalse(staff_role.has_user(staff), 'Should be removed from the staff')

        first_res = self.client.delete(u'{url}?roles={roles}'.format(
            url=self.api_url,
            roles=roles_to_delete,
        ))

        assert_proper_deletion(first_res)

        second_res = self.client.delete(u'{url}?roles={roles}'.format(
            url=self.api_url,
            roles=roles_to_delete,
        ))

        assert_proper_deletion(second_res)

    def test_put_de_duplication(self):
        instructor = UserFactory.create()
        instructor_to_be = UserFactory.create()

        instructor_role = CourseInstructorRole(self.course.id)
        staff_role = CourseStaffRole(self.course.id)

        res = self.client.put(self.api_url, content_type='application/json', data=json.dumps({
            'roles': {
                'staff': [
                    instructor_to_be.username,
                ],
                'instructor': [
                    instructor.email,
                ],
            },
        }))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        duplicate_res = self.client.put(self.api_url, content_type='application/json', data=json.dumps({
            'roles': {
                'instructor': [
                    instructor_to_be.username,
                ],
            },
        }))

        self.assertEqual(duplicate_res.status_code, status.HTTP_200_OK)

        # Make both are still instructors
        self.assertTrue(instructor_role.has_user(instructor), 'Should be an instructor')
        self.assertTrue(instructor_role.has_user(instructor_to_be), 'Should have become an instructor')
        self.assertFalse(staff_role.has_user(instructor_to_be),
                         'Should be removed from the staff, there should be no duplicates')
