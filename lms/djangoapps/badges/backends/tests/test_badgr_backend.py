"""
Tests for BadgrBackend
"""
from datetime import datetime

import ddt
from django.db.models.fields.files import ImageFieldFile
from django.test.utils import override_settings
from django.core.cache import caches
from lazy.lazy import lazy
from mock import patch, Mock, call

from badges.backends.badgr import BadgrBackend
from badges.models import BadgeAssertion
from badges.tests.factories import BadgeClassFactory
from openedx.core.lib.tests.assertions.events import assert_event_matches
from student.tests.factories import UserFactory, CourseEnrollmentFactory
from track.tests import EventTrackingTestCase
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


BADGR_SETTINGS_API_V1 = {
    'BADGR_API_VERSION': 'v1',
    'BADGR_BASE_URL': 'https://example.com',
    'BADGR_ISSUER_SLUG': 'test-issuer',
    'BADGR_API_TOKEN': '12345',
    'BADGR_API_NOTIFICATIONS_ENABLED': True
}

BADGR_SETTINGS_API_V2 = {
    'BADGR_API_VERSION': 'v2',
    'BADGR_BASE_URL': 'https://example.com',
    'BADGR_ISSUER_SLUG': 'test-issuer',
    'BADGR_API_TOKEN': '12345',
    'BADGR_API_REFRESH_TOKEN': '678910',
    'BADGR_API_NOTIFICATIONS_ENABLED': True
}

# Should be the hashed result of test_slug as the slug, and test_component as the component
EXAMPLE_SLUG = '15bb687e0c59ef2f0a49f6838f511bf4ca6c566dd45da6293cabbd9369390e1a'


# pylint: disable=protected-access
@ddt.ddt
class BadgrBackendTestCase(ModuleStoreTestCase, EventTrackingTestCase):
    """
    Tests the BadgeHandler object using Badgr API v1 and v2
    """

    ENABLED_CACHES = ['default', 'mongo_metadata_inheritance', 'loc_cache', 'badgr_api_token_cache']

    def setUp(self):
        """
        Create a course and user to test with.
        """
        super(BadgrBackendTestCase, self).setUp()
        # Need key to be deterministic to test slugs.
        self.course = CourseFactory.create(
            org='edX', course='course_test', run='test_run', display_name='Badged',
            start=datetime(year=2015, month=5, day=19),
            end=datetime(year=2015, month=5, day=20)
        )
        self.user = UserFactory.create(email='example@example.com')
        CourseEnrollmentFactory.create(user=self.user, course_id=self.course.location.course_key, mode='honor')
        # Need to empty this on each run.
        BadgrBackend.badges = []
        self.badge_class = BadgeClassFactory.create(course_id=self.course.location.course_key)
        self.legacy_badge_class = BadgeClassFactory.create(
            course_id=self.course.location.course_key, issuing_component=''
        )
        self.no_course_badge_class = BadgeClassFactory.create()

    @lazy
    def handler(self):
        """
        Lazily loads a BadgeHandler object for the current course. Can't do this on setUp because the settings
        overrides aren't in place.
        """
        return BadgrBackend()

    @override_settings(**BADGR_SETTINGS_API_V1)
    def test_urls_v1(self):
        """
        Make sure the handler generates the correct URLs for different API v1 tasks.
        """
        self.assertEqual(self.handler._base_url, 'https://example.com/v1')
        self.assertEqual(self.handler._issuer_base_url, 'https://example.com/v1/issuer/issuers')
        self.assertEqual(self.handler._badge_create_url, 'https://example.com/v1/issuer/issuers/test-issuer/badges')
        self.assertEqual(
            self.handler._badge_url('test_slug_here'),
            'https://example.com/v1/issuer/issuers/test-issuer/badges/test_slug_here'
        )
        self.assertEqual(
            self.handler._assertion_url('another_test_slug'),
            'https://example.com/v1/issuer/issuers/test-issuer/badges/another_test_slug/assertions'
        )

    @override_settings(**BADGR_SETTINGS_API_V1)
    def check_headers_v1(self, headers):
        """
        Verify the a headers dict from a requests call matches the proper auth info.
        """
        self.assertEqual(headers, {'Authorization': 'Token 12345'})

    @override_settings(**BADGR_SETTINGS_API_V1)
    def test_get_headers_v1(self):
        """
        Check to make sure the handler generates appropriate HTTP headers.
        """
        self.check_headers_v1(self.handler._get_headers())


    @patch('requests.post')
    @patch('requests.get')
    @override_settings(**BADGR_SETTINGS_API_V1)
    def test_create_badge(self, get, post):
        """
        Verify badge spec creation works.
        """
        response = Mock()
        response.status_code = 404
        get.return_value = response
        self.handler._create_badge(self.badge_class)
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://example.com/v1/issuer/issuers/test-issuer/badges')
        self.assertEqual(kwargs['files']['image'][0], self.badge_class.image.name)
        self.assertIsInstance(kwargs['files']['image'][1], ImageFieldFile)
        self.assertEqual(kwargs['files']['image'][2], 'image/png')
        # TODO: YOU CAN'T ACTUALLY CREATE A BADGE AND PREDICT THE SLUG FROM BADGR ANY MORE
        # COMMENTING THESE UNTIL A REWORK WHERE WE SEPARATE SLUG AND BACKEND ID
        # AND ASSIGN THE BACKEND ID BASED ON BACKEND API RESPONSE
        # self.check_headers_v1(kwargs['headers'])
        # self.assertEqual(
        #     kwargs['data'],
        #     {
        #         'name': 'Test Badge',
        #         'slug': EXAMPLE_SLUG,
        #         'criteria': 'https://example.com/syllabus',
        #         'description': "Yay! It's a test badge.",
        #     }
        # )

    @patch('requests.get')
    @patch('requests.post')
    @override_settings(**BADGR_SETTINGS_API_V1)
    def test_ensure_badge_created_cache(self, post, get):
        """
        Make sure ensure_badge_created doesn't call create_badge if we know the badge is already there.
        """
        response = Mock()
        response.status_code = 200
        get.return_value = response
        BadgrBackend.badges.append(EXAMPLE_SLUG)
        self.handler._create_badge = Mock()
        self.handler._ensure_badge_created(self.badge_class)
        self.assertFalse(self.handler._create_badge.called)

    @patch('requests.get')
    @patch('requests.post')
    @override_settings(**BADGR_SETTINGS_API_V1)
    def test_ensure_badge_created_checks_v1(self, post, get):
        response = Mock()
        response.status_code = 200
        get.return_value = response
        self.assertNotIn('test_componenttest_slug', BadgrBackend.badges)
        self.handler._create_badge = Mock()
        self.handler._ensure_badge_created(self.badge_class)
        self.assertTrue(get.called)
        args, kwargs = get.call_args
        # self.assertEqual(
        #     args[0],
        #     'https://example.com/v1/issuer/issuers/test-issuer/badges/' +
        #     EXAMPLE_SLUG
        # )
        # self.check_headers_v1(kwargs['headers'])
        # self.assertIn(EXAMPLE_SLUG, BadgrBackend.badges)
        self.assertFalse(self.handler._create_badge.called)

    @patch('requests.post')
    @patch('requests.get')
    @override_settings(**BADGR_SETTINGS_API_V1)
    def test_ensure_badge_created_creates_v1(self, post, get):
        response = Mock()
        response.status_code = 404
        get.return_value = response
        self.assertNotIn(EXAMPLE_SLUG, BadgrBackend.badges)
        self.handler._create_badge = Mock()
        self.handler._ensure_badge_created(self.badge_class)
        self.assertTrue(self.handler._create_badge.called)
        self.assertEqual(self.handler._create_badge.call_args, call(self.badge_class))
        # self.assertIn(EXAMPLE_SLUG, BadgrBackend.badges)

    @patch('requests.post')
    @override_settings(**BADGR_SETTINGS_API_V1)
    def test_badge_creation_event_v1(self, post):
        result = {
            'slug': 'https://www.example.com/v1/issuer/issuers/test-issuer/badges/test-badge-slug/test-assertion-slug',
            'image': 'https://www.example.com/example.png',
        }
        response = Mock()
        response.json.return_value = result
        post.return_value = response
        self.recreate_tracker()
        self.handler._create_assertion(self.badge_class, self.user, 'https://example.com/irrefutable_proof')
        args, kwargs = post.call_args
        # self.assertEqual(
        #     args[0],
        #     'https://example.com/v1/issuer/issuers/test-issuer/badges/' +
        #     EXAMPLE_SLUG +
        #     '/assertions'
        # )
        self.check_headers_v1(kwargs['headers'])
        assertion = BadgeAssertion.objects.get(user=self.user, badge_class__course_id=self.course.location.course_key)
        self.assertEqual(assertion.data, result)
        self.assertEqual(assertion.image_url, 'https://www.example.com/example.png')
        self.assertEqual(assertion.assertion_url, 'https://www.example.com/v1/issuer/issuers/test-issuer/badges/test-badge-slug/test-assertion-slug')
        self.assertEqual(kwargs['json'], {
            'recipient_identifier': 'example@example.com',
            'recipient_type': 'email',
            'evidence_items': [{ 'evidence_url': 'https://example.com/irrefutable_proof'}],
            'create_notification': True,
        })
        # TODO: fix this... we don't know that badge_slug is 'test_slug' b/c they are randomized
        # assert_event_matches({
        #     'name': 'edx.badge.assertion.created',
        #     'data': {
        #         'user_id': self.user.id,
        #         'course_id': unicode(self.course.location.course_key),
        #         'enrollment_mode': 'honor',
        #         'assertion_id': assertion.id,
        #         'badge_name': 'Test Badge',
        #         'badge_slug': 'test_slug',
        #         'issuing_component': 'test_component',
        #         'assertion_image_url': 'http://www.example.com/example.png',
        #         'assertion_json_url': 'http://www.example.com/example',
        #         'issuer': 'https://example.com/v1/issuer/issuers/test-issuer',
        #     }
        # }, self.get_event())

    def _set_token_caches(self):
        caches['badgr_api_token_cache'].set('badgr_api_auth_token', 11111, 86400)
        caches['badgr_api_token_cache'].set('badgr_api_refresh_token', 22222, 86400)

    @override_settings(**BADGR_SETTINGS_API_V2)
    def test_urls_v2(self):
        """
        Make sure the handler generates the correct URLs for different API v2 tasks.
        """
        self._set_token_caches()
        self.assertEqual(self.handler._base_url, 'https://example.com/v2')
        self.assertEqual(self.handler._issuer_base_url, 'https://example.com/v2/issuers')
        self.assertEqual(self.handler._badge_create_url, 'https://example.com/v2/issuers/test-issuer/badgeclasses')
        self.assertEqual(
            self.handler._badge_url('test_slug_here'),
            'https://example.com/v2/badgeclasses/test_slug_here'
        )
        self.assertEqual(
            self.handler._assertion_url('another_test_slug'),
            'https://example.com/v2/badgeclasses/another_test_slug/assertions'
        )

    @override_settings(**BADGR_SETTINGS_API_V2)
    def test_get_headers_token_cached(self):
        """
        Check to make sure a cached auth token is returned if available
        """
        self._set_token_caches()
        self.assertEqual(self.handler._get_headers(), {'Authorization': 'Bearer 11111'})

    @patch('requests.post')
    @override_settings(**BADGR_SETTINGS_API_V2)
    def test_get_headers_token_not_cached(self, post):
        """
        Make sure we get a new auth and refresh token using existing refresh token, if
        auth token is not available (don't use auth token from settings).
        """
        self._set_token_caches()
        caches['badgr_api_token_cache'].delete('badgr_api_auth_token')
        result = {
            'access_token': '55555',
            'refresh_token': '66666'
        }
        response = Mock()
        response.status_code = 200
        response.json.return_value = result
        post.return_value = response

        self.assertEqual(self.handler._get_headers(), {'Authorization': 'Bearer 55555'})

        # make sure stored in cache
        cached_auth = caches['badgr_api_token_cache'].get('badgr_api_auth_token')
        cached_refresh = caches['badgr_api_token_cache'].get('badgr_api_refresh_token')
        self.assertEqual(cached_auth, '55555')
        self.assertEqual(cached_refresh, '66666')
        self.assertEqual(self.handler._get_headers(), {'Authorization': 'Bearer 55555'})
