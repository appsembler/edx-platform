import json

import ddt
from django.urls import reverse

from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import ToyCourseFactory

from common.djangoapps.student.roles import CourseStaffRole
from openedx.core.djangoapps.course_groups import cohorts

from .test_utils import lms_multi_tenant_test, with_organization_context, create_org_user


@lms_multi_tenant_test
@ddt.ddt
class TestCohortMultiTenantApi(SharedModuleStoreTestCase):
    """
    Tests for cohort API endpoints multi-tenancy.
    """
    USERNAME = 'honor'
    USER_MAIL = 'honor@example.com'
    PASSWORD = 'password'

    @classmethod
    def setUpClass(cls):
        super(TestCohortMultiTenantApi, cls).setUpClass()
        with with_organization_context('blue') as blue_org:
            cls.user = create_org_user(blue_org, username=cls.USERNAME, email=cls.USER_MAIL, password=cls.PASSWORD)
            # TODO: Remove `is_staff=True`
            cls.instructor = create_org_user(blue_org, is_amc_admin=True, password=cls.PASSWORD)
            cls.course_key = ToyCourseFactory.create().id
            CourseStaffRole(cls.course_key).add_users(cls.instructor)

    def test_add_users_to_cohort_single_tenant(self):
        """
        Sanity check for the POST method for adding users to a cohort.

        This method duplicates `TestCohortApi.test_add_users_to_cohort`. If this method fails, then the platform
        have changed and we need to revisit our multi-tenancy accordingly.
        """
        cohorts.add_cohort(self.course_key, 'DEFAULT', 'random')
        cohort_id = 1
        path = reverse('api_cohorts:cohort_users',
                       kwargs={'course_key_string': str(self.course_key), 'cohort_id': cohort_id})
        assert self.client.login(username=self.instructor.username, password=self.PASSWORD)
        response = self.client.post(
            path=path,
            data=json.dumps({'users': [self.USER_MAIL, ]}),
            content_type='application/json')
        assert response.status_code == 200, response.content.decode('utf-8')

    # def test_add_learner_in_multiple_sites(self):
    #     assert False, 'TODO: Implement'
    #
    # def test_remove_learner_in_muliple_sites(self):
    #     assert False, 'TODO: Implement'
    #
    # def test_staff_cannot_access_other_site_courses(self):
    #     assert False, 'TODO: Implement'

    @ddt.data(
        {'username': USERNAME, 'status': 204},
        {'username': 'doesnotexist', 'status': 404},
        {'username': None, 'status': 404},
    )
    @ddt.unpack
    def test_remove_user_from_cohort_single_tenant(self, username, status):
        """
        Sanity check for the DELETE method for removing an user from a cohort.

        This method duplicates `TestCohortApi.test_remove_user_from_cohort`. If this method fails, then the platform
        have changed and we need to revisit our multi-tenancy accordingly.
        """
        cohort = cohorts.add_cohort(self.course_key, 'DEFAULT', 'random')
        cohorts.add_user_to_cohort(cohort, self.USERNAME)
        cohort_id = 1
        path = reverse('api_cohorts:cohort_users',
                       kwargs={'course_key_string': str(self.course_key), 'cohort_id': cohort_id, 'username': username})
        assert self.client.login(username=self.instructor.username, password=self.PASSWORD)
        response = self.client.delete(path=path)
        assert response.status_code == status, response.content.decode('utf-8')
