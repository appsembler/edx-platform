""" Test Student helpers with Auth0 """

import ddt
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from mock import patch

from openedx.core.djangoapps.site_configuration.tests.test_util import with_site_configuration
from student.helpers import get_next_url_for_login_page

from site_config_client.openedx.test_helpers import override_site_config


@ddt.ddt
class TestAuth0DisablingLogistrationForm(TestCase):
    """Disable login/registration forms when Auth0 is enabled."""

    def setUp(self):
        super().setUp()
        self.request_factory = RequestFactory()

    @patch('student.helpers.third_party_auth.pipeline.get')
    @ddt.data(
        {
            'http_method': 'GET',
            'running_pipeline': False,
        },
        {
            'http_method': 'POST',
            'running_pipeline': False,
        },
    )
    @ddt.unpack
    @with_site_configuration()
    def test_third_party_auth_hint(self, mock_get_pipeline, http_method, running_pipeline):
        mock_get_pipeline.return_value = running_pipeline

        next_url = '/dashboard'
        if http_method == 'GET':
            request = self.request_factory.get(settings.LOGIN_URL + "?next={url}".format(url=next_url))
        else:
            assert http_method == 'POST', 'Sanity check: Only `GET` and `POST` are supported'
            request = self.request_factory.post(settings.LOGIN_URL, {'next': next_url})

        request.META['HTTP_ACCEPT'] = 'text/html'
        middleware = SessionMiddleware()
        middleware.process_request(request)  # Annotate the request object with a session
        request.session.save()

        with override_site_config('admin', ENABLE_TAHOE_AUTH0=True):
            auth0_next = get_next_url_for_login_page(request)
        assert auth0_next == '/dashboard?tpa_hint=tahoe-auth0', 'tahoe-auth0 is used when `is_tahoe_auth0_enabled`'

        with override_settings(FEATURES=dict(settings.FEATURES, THIRD_PARTY_AUTH_HINT='oa2-google-oauth2')):
            with override_site_config('admin', ENABLE_TAHOE_AUTH0=True):
                tpa_hinted_next = get_next_url_for_login_page(request)
        assert tpa_hinted_next == '/dashboard?tpa_hint=oa2-google-oauth2', 'THIRD_PARTY_AUTH_HINT overrides tahoe-auth0'

        default_next = get_next_url_for_login_page(request)
        assert default_next == '/dashboard', 'Sanity check: Should provide no tpa_hint by default'
