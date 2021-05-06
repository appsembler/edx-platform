import json

import ddt
import six
from six.moves import range
from django.urls import reverse

from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import ToyCourseFactory

from openedx.core.djangoapps.course_groups import cohorts
from openedx.core.djangoapps.course_groups.tests.helpers import CohortFactory

from .test_utils import lms_multi_tenant_test, with_organization_context


USERNAME = 'honor'
USER_MAIL = 'honor@example.com'
SETTINGS_PAYLOAD = '{"is_cohorted": true}'
HANDLER_POST_PAYLOAD = '{"name":"Default","user_count":0,"assignment_type":"random","user_partition_id":null\
,"group_id":null}'
HANDLER_PATCH_PAYLOAD = '{"name":"Default Group","group_id":null,"user_partition_id":null,"assignment_type":"random"}'
ADD_USER_PAYLOAD = json.dumps({'users': [USER_MAIL, ]})
CSV_DATA = '''email,cohort\n{},DEFAULT'''.format(USER_MAIL)


@lms_multi_tenant_test
@ddt.ddt
class TestCohortMultiTenantApi(SharedModuleStoreTestCase):
    """
    Tests for cohort API endpoints
    """

    password = 'password'

    @classmethod
    def setUpClass(cls):
        super(TestCohortMultiTenantApi, cls).setUpClass()
        cls.user = UserFactory(username=USERNAME, email=USER_MAIL, password=cls.password)
        cls.staff_user = UserFactory(is_staff=True, password=cls.password)
        cls.course_key = ToyCourseFactory.create().id
        cls.course_str = six.text_type(cls.course_key)

    @ddt.data(
        {'is_staff': False, 'status': 403},
        {'is_staff': True, 'status': 200},
    )
    @ddt.unpack
    def test_list_users_in_cohort(self, is_staff, status):
        """
        Test GET method for listing users in a cohort.
        """
        users = [UserFactory() for _ in range(5)]
        cohort = CohortFactory(course_id=self.course_key, users=users)
        path = reverse(
            'api_cohorts:cohort_users',
            kwargs={'course_key_string': self.course_str, 'cohort_id': cohort.id}
        )
        self.user = self.staff_user if is_staff else self.user
        assert self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(
            path=path
        )
        assert response.status_code == status

        if status == 200:
            results = json.loads(response.content.decode('utf-8'))['results']
            expected_results = [{
                'username': user.username,
                'email': user.email,
                'name': u'{} {}'.format(user.first_name, user.last_name)
            } for user in users]
            assert results == expected_results

    @ddt.data({'is_staff': False, 'payload': ADD_USER_PAYLOAD, 'status': 403},
              {'is_staff': True, 'payload': ADD_USER_PAYLOAD, 'status': 200}, )
    @ddt.unpack
    def test_add_users_to_cohort(self, is_staff, payload, status):
        """
        Test POST method for adding users to a cohort
        """
        cohorts.add_cohort(self.course_key, "DEFAULT", "random")
        cohort_id = 1
        path = reverse('api_cohorts:cohort_users',
                       kwargs={'course_key_string': self.course_str, 'cohort_id': cohort_id})
        user = self.staff_user if is_staff else self.user
        assert self.client.login(username=user.username, password=self.password)
        response = self.client.post(
            path=path,
            data=payload,
            content_type='application/json')
        assert response.status_code == status

    @ddt.data({'is_staff': False, 'username': USERNAME, 'status': 403},
              {'is_staff': True, 'username': USERNAME, 'status': 204},
              {'is_staff': True, 'username': 'doesnotexist', 'status': 404},
              {'is_staff': False, 'username': None, 'status': 403},
              {'is_staff': True, 'username': None, 'status': 404}, )
    @ddt.unpack
    def test_remove_user_from_cohort(self, is_staff, username, status):
        """
        Test DELETE method for removing an user from a cohort.
        """
        cohort = cohorts.add_cohort(self.course_key, "DEFAULT", "random")
        cohorts.add_user_to_cohort(cohort, USERNAME)
        cohort_id = 1
        path = reverse('api_cohorts:cohort_users',
                       kwargs={'course_key_string': self.course_str, 'cohort_id': cohort_id, 'username': username})
        user = self.staff_user if is_staff else self.user
        assert self.client.login(username=user.username, password=self.password)
        response = self.client.delete(path=path)
        assert response.status_code == status
