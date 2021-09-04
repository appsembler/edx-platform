from django.core.exceptions import ValidationError
from unittest.mock import patch, Mock
import pytest
import ddt

from django.test import TestCase

from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locator import CourseLocator

from student.tests.factories import UserFactory
from openedx.core.djangoapps.user_authn.views.register import _skip_activation_email
from openedx.core.djangoapps.appsembler.api.helpers import as_course_key
from openedx.core.djangoapps.appsembler.api.tests.factories import COURSE_ID_STR_TEMPLATE

from openedx.core.djangoapps.appsembler.api.helpers import (
    skip_registration_email_for_registration_api,
    normalize_bool_param,
)


class CourseKeyHelperTest(TestCase):

    def setUp(self):
        self.course_key_string = COURSE_ID_STR_TEMPLATE.format(1)
        self.course_key = CourseKey.from_string(self.course_key_string)

    def test_from_valid_string(self):
        course_key = as_course_key(self.course_key_string)
        assert isinstance(course_key, CourseKey)
        assert course_key == self.course_key
        assert course_key is not self.course_key

    def test_from_invalid_string(self):
        with pytest.raises(InvalidKeyError):
            as_course_key('some invalid string')

    def test_from_course_key(self):
        course_key = as_course_key(self.course_key)
        assert isinstance(course_key, CourseKey)
        assert course_key == self.course_key
        assert course_key is self.course_key

    def test_from_course_locator(self):
        course_locator = CourseLocator.from_string(
            self.course_key_string)
        course_key = as_course_key(course_locator)
        assert isinstance(course_key, CourseKey)
        assert course_key == self.course_key
        assert course_key is course_locator

    def test_from_invalid_type(self):
        with pytest.raises(TypeError):
            as_course_key(dict(foo='bar'))


@ddt.ddt
class TestAPISendActivationEmail(TestCase):
    """
    Tests for _skip_activation_email for Tahoe Registration API and the related helpers.
    """

    @patch.dict('django.conf.settings.FEATURES', {'SKIP_EMAIL_VALIDATION': False})
    def test_skip_for_api_callers_upon_request(self):
        """
        Email should not be sent if the API caller wants to skip it.
        """
        user = UserFactory.create()

        helper_path = 'openedx.core.djangoapps.user_authn.views.register.skip_registration_email_for_registration_api'
        with patch(helper_path, return_value=True):
            assert _skip_activation_email(user, {}, None), 'API requested: email can be skipped by AMC admin'

    @ddt.unpack
    @ddt.data(
        # The function should return the opposite of the parameter
        # skip_registration_email_for_registration_api == not send_activation_email
        {'post': {'send_activation_email': True}, 'should_skip': False},
        {'post': {'send_activation_email': False}, 'should_skip': True},
        {'post': {'send_activation_email': 'True'}, 'should_skip': False},
        {'post': {'send_activation_email': 'False'}, 'should_skip': True},
        {'post': {'send_activation_email': 'true'}, 'should_skip': False},
        {'post': {'send_activation_email': 'false'}, 'should_skip': True},
        {'post': {}, 'should_skip': False},  # By default, the email should be sent
    )
    def test_skip_registration_email_for_registration_api(self, post, should_skip):
        """
        Tests for the skip_registration_email_for_registration_api helper.

         - This helper takes the `send_activation_email` parameter (defaults to True)
         - Then normalize it to ensure it's converted to a sane boolean.
         - Then it negates it via the `not` parameter.
        """
        request = Mock(POST=post, method='POST')
        assert skip_registration_email_for_registration_api(request) == should_skip

    @ddt.data(True, False, 'True', 'False', 'true', 'false')
    def test_normalize_bool_param(self, unnormalized):
        expected_map = {
            True: True,
            False: False,
            'True': True,
            'False': False,
            'true': True,
            'false': False
        }
        normalized = normalize_bool_param(unnormalized)
        assert normalized == expected_map[unnormalized]

    @ddt.data(None, 0, 'f', 't', '')
    def test_normalize_bool_param_error(self, incorrect_value):
        with self.assertRaisesRegex(ValidationError, 'invalid value ".*" for boolean type'):
            normalize_bool_param(incorrect_value)
