""" Test Student helpers """


import logging

import ddt
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from mock import patch
from mock import Mock
from testfixtures import LogCapture

from openedx.core.djangoapps.site_configuration.tests.test_util import with_site_configuration_context
from student.helpers import get_next_url_for_login_page, sanitize_next_parameter

LOGGER_NAME = "student.helpers"


@ddt.ddt
class TestLoginHelper(TestCase):
    """Test login helper methods."""
    static_url = settings.STATIC_URL

    def setUp(self):
        super(TestLoginHelper, self).setUp()
        self.request = RequestFactory()

    @staticmethod
    def _add_session(request):
        """Annotate the request object with a session"""
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()

    @ddt.data(
        (logging.WARNING, "WARNING", "https://www.amazon.com", "text/html", None,
         "Unsafe redirect parameter detected after login page: 'https://www.amazon.com'"),
        # TODO: Fix the test case below. Likely broken because of our theme fixes -- Omar
        #      (logging.WARNING, "WARNING", "testserver/edx.org/images/logo", "text/html", None,
        #       "Redirect to theme content detected after login page: 'testserver/edx.org/images/logo'"),
        (logging.INFO, "INFO", "favicon.ico", "image/*", "test/agent",
         "Redirect to non html content 'image/*' detected from 'test/agent' after login page: 'favicon.ico'"),
        (logging.WARNING, "WARNING", "https://www.test.com/test.jpg", "image/*", None,
         "Unsafe redirect parameter detected after login page: 'https://www.test.com/test.jpg'"),
        (logging.INFO, "INFO", static_url + "dummy.png", "image/*", "test/agent",
         "Redirect to non html content 'image/*' detected from 'test/agent' after login page: '" + static_url +
         "dummy.png" + "'"),
        (logging.WARNING, "WARNING", "test.png", "text/html", None,
         "Redirect to url path with specified filed type 'image/png' not allowed: 'test.png'"),
        (logging.WARNING, "WARNING", static_url + "dummy.png", "text/html", None,
         "Redirect to url path with specified filed type 'image/png' not allowed: '" + static_url + "dummy.png" + "'"),
    )
    @ddt.unpack
    def test_next_failures(self, log_level, log_name, unsafe_url, http_accept, user_agent, expected_log):
        """ Test unsafe next parameter """
        with LogCapture(LOGGER_NAME, level=log_level) as logger:
            req = self.request.get(settings.LOGIN_URL + "?next={url}".format(url=unsafe_url))
            req.META["HTTP_ACCEPT"] = http_accept
            req.META["HTTP_USER_AGENT"] = user_agent
            get_next_url_for_login_page(req)
            logger.check(
                (LOGGER_NAME, log_name, expected_log)
            )

    @ddt.data(
        ('/dashboard', 'text/html', 'testserver'),
        ('https://edx.org/courses', 'text/*', 'edx.org'),
        ('https://test.edx.org/courses', '*/*', 'edx.org'),
        ('https://test2.edx.org/courses', 'image/webp, */*;q=0.8', 'edx.org'),
    )
    @ddt.unpack
    @override_settings(LOGIN_REDIRECT_WHITELIST=['test.edx.org', 'test2.edx.org'])
    def test_safe_next(self, next_url, http_accept, host):
        """ Test safe next parameter """
        req = self.request.get(settings.LOGIN_URL + "?next={url}".format(url=next_url), HTTP_HOST=host)
        req.META["HTTP_ACCEPT"] = http_accept
        next_page = get_next_url_for_login_page(req)
        self.assertEqual(next_page, next_url)

    tpa_hint_test_cases = [
        # Test requests outside the TPA pipeline - tpa_hint should be added.
        (None, '/dashboard', '/dashboard', False),
        ('', '/dashboard', '/dashboard', False),
        ('', '/dashboard?tpa_hint=oa2-google-oauth2', '/dashboard?tpa_hint=oa2-google-oauth2', False),
        # TODO: Fix ('saml-idp', '/dashboard', '/dashboard?tpa_hint=saml-idp', False). This test is likely to be
        #       broken because of our SAML customizations -- Omar
        # THIRD_PARTY_AUTH_HINT can be overridden via the query string
        ('saml-idp', '/dashboard?tpa_hint=oa2-google-oauth2', '/dashboard?tpa_hint=oa2-google-oauth2', False),

        # Test requests inside the TPA pipeline - tpa_hint should not be added, preventing infinite loop.
        (None, '/dashboard', '/dashboard', True),
        ('', '/dashboard', '/dashboard', True),
        ('', '/dashboard?tpa_hint=oa2-google-oauth2', '/dashboard?tpa_hint=oa2-google-oauth2', True),
        ('saml-idp', '/dashboard', '/dashboard', True),
        # OK to leave tpa_hint overrides in place.
        ('saml-idp', '/dashboard?tpa_hint=oa2-google-oauth2', '/dashboard?tpa_hint=oa2-google-oauth2', True),
    ]
    tpa_hint_test_cases_with_method = [
        (method, *test_case)
        for test_case in tpa_hint_test_cases
        for method in ['GET', 'POST']
    ]

    @patch('student.helpers.third_party_auth.pipeline.get')
    @ddt.data(*tpa_hint_test_cases_with_method)
    @ddt.unpack
    def test_third_party_auth_hint(
        self,
        method,
        tpa_hint,
        next_url,
        expected_url,
        running_pipeline,
        mock_running_pipeline,
    ):
        mock_running_pipeline.return_value = running_pipeline

        def validate_login():
            """
            Assert that get_next_url_for_login_page returns as expected.
            """
            if method == 'GET':
                req = self.request.get(settings.LOGIN_URL + "?next={url}".format(url=next_url))
            elif method == 'POST':
                req = self.request.post(settings.LOGIN_URL, {'next': next_url})
            req.META["HTTP_ACCEPT"] = "text/html"
            self._add_session(req)
            next_page = get_next_url_for_login_page(req)
            self.assertEqual(next_page, expected_url)

        with override_settings(FEATURES=dict(settings.FEATURES, THIRD_PARTY_AUTH_HINT=tpa_hint)):
            validate_login()

        with with_site_configuration_context(configuration=dict(THIRD_PARTY_AUTH_HINT=tpa_hint)):
            validate_login()

    @patch('student.helpers._get_redirect_to', Mock(return_value=None))
    def test_custom_tahoe_site_redirect_lms(self):
        """
        Allow site admins to customize the default after-login URL.

        Appsembler: This is specific to Tahoe and mostly not suitable for contribution to upstream.
        """
        request = Mock(GET={}, POST={})
        assert '/dashboard' == get_next_url_for_login_page(request), 'Default should be /dashboard'

        with with_site_configuration_context(configuration={
            'LOGIN_REDIRECT_URL': '/about'
        }):
            assert '/about' == get_next_url_for_login_page(request), 'Custom redirect should be used'

        with with_site_configuration_context(configuration={
            'LOGIN_REDIRECT_URL': ''  # Falsy or empty URLs should not be used
        }):
            assert '/dashboard' == get_next_url_for_login_page(request), 'Falsy url should default to dashboard'

    def test_sanitize_next_param(self):
        # Valid URL with plus - change the plus symbol to ASCII code
        next_param = 'courses/course-v1:abc-sandbox+ACC-PTF+C/course'
        expected_result = 'courses/course-v1:abc-sandbox%2BACC-PTF%2BC/course'
        self.assertEqual(sanitize_next_parameter(next_param), expected_result)

        # Valid URL without plus - keep the next_param as it is
        next_param = 'courses/course-v1:abc-sandbox/course'
        self.assertEqual(sanitize_next_parameter(next_param), next_param)

        # Empty string - keep the next_param as it is
        next_param = ''
        self.assertEqual(sanitize_next_parameter(next_param), next_param)

        # None input - keep the next_param as it is
        next_param = None
        self.assertEqual(sanitize_next_parameter(next_param), next_param)

        # Invalid pattern - keep the next_param as it is
        next_param = 'some/other/path'
        self.assertEqual(sanitize_next_parameter(next_param), next_param)

        # Invalid URL with space - replace the ' ' with '+' and encode it
        expected_result = 'courses/course-v1:abc-sandbox%2BACC-PTF%2BC/course'

        next_param = 'courses/course-v1:abc-sandbox ACC-PTF C/course'
        self.assertEqual(sanitize_next_parameter(next_param), expected_result)

        next_param = 'courses/course-v1:abc-sandbox ACC-PTF+C/course'
        self.assertEqual(sanitize_next_parameter(next_param), expected_result)

        next_param = 'courses/course-v1:abc-sandbox+ACC-PTF C/course'
        self.assertEqual(sanitize_next_parameter(next_param), expected_result)

        # Invalid URL with encoded space - replace the '%20' with '+' and encode it
        expected_result = 'courses/course-v1:abc-sandbox%2BACC-PTF%2BC/course'

        next_param = 'courses/course-v1:abc-sandbox%20ACC-PTF%20C/course'
        self.assertEqual(sanitize_next_parameter(next_param), expected_result)

        next_param = 'courses/course-v1:abc-sandbox%20ACC-PTF+C/course'
        self.assertEqual(sanitize_next_parameter(next_param), expected_result)

        next_param = 'courses/course-v1:abc-sandbox+ACC-PTF%20C/course'
        self.assertEqual(sanitize_next_parameter(next_param), expected_result)
