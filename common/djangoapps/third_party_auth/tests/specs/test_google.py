"""Integration tests for Google providers."""
import base64
import hashlib
import hmac
from django.conf import settings
from django.urls import reverse
import json
from mock import patch
from social_core.exceptions import AuthException
from student.tests.factories import UserFactory
from third_party_auth import pipeline
from third_party_auth.tests.specs import base


class GoogleOauth2IntegrationTest(base.Oauth2IntegrationTest):
    """Integration tests for provider.GoogleOauth2."""

    def setUp(self):
        super(GoogleOauth2IntegrationTest, self).setUp()
        self.provider = self.configure_google_provider(
            enabled=True,
            visible=True,
            key='google_oauth2_key',
            secret='google_oauth2_secret',
        )

    TOKEN_RESPONSE_DATA = {
        'access_token': 'access_token_value',
        'expires_in': 'expires_in_value',
        'id_token': 'id_token_value',
        'token_type': 'token_type_value',
    }
    USER_RESPONSE_DATA = {
        'email': 'user@email.com',
        'family_name': 'family_name_value',
        'given_name': 'given_name_value',
        'id': 'id_value',
        'link': 'link_value',
        'locale': 'locale_value',
        'name': 'name_value',
        'picture': 'picture_value',
        'verified_email': 'verified_email_value',
    }

    def get_username(self):
        return self.get_response_data().get('email').split('@')[0]

    def assert_redirect_to_provider_looks_correct(self, response):
        super(GoogleOauth2IntegrationTest, self).assert_redirect_to_provider_looks_correct(response)
        self.assertIn('google.com', response['Location'])

    def test_custom_form(self):
        """
        Use the Google provider to test the custom login/register form feature.
        """
        # The pipeline starts by a user GETting /auth/login/google-oauth2/?auth_entry=custom1
        # Synthesize that request and check that it redirects to the correct
        # provider page.
        auth_entry = 'custom1'  # See definition in lms/envs/test.py
        login_url = pipeline.get_login_url(self.provider.provider_id, auth_entry)
        login_url += "&next=/misc/final-destination"
        self.assert_redirect_to_provider_looks_correct(self.client.get(login_url))

        def fake_auth_complete(inst, *args, **kwargs):
            """ Mock the backend's auth_complete() method """
            kwargs.update({'response': self.get_response_data(), 'backend': inst})
            return inst.strategy.authenticate(*args, **kwargs)

        # Next, the provider makes a request against /auth/complete/<provider>.
        complete_url = pipeline.get_complete_url(self.provider.backend_name)
        with patch.object(self.provider.backend_class, 'auth_complete', fake_auth_complete):
            response = self.client.get(complete_url)
        # This should redirect to the custom login/register form:
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/auth/custom_auth_entry')

        response = self.client.get(response['Location'])
        self.assertEqual(response.status_code, 200)
        self.assertIn('action="/misc/my-custom-registration-form" method="post"', response.content)
        data_decoded = base64.b64decode(response.context['data'])
        data_parsed = json.loads(data_decoded)
        # The user's details get passed to the custom page as a base64 encoded query parameter:
        self.assertEqual(data_parsed, {
            'auth_entry': 'custom1',
            'backend_name': 'google-oauth2',
            'provider_id': 'oa2-google-oauth2',
            'user_details': {
                'username': 'user',
                'email': 'user@email.com',
                'fullname': 'name_value',
                'first_name': 'given_name_value',
                'last_name': 'family_name_value',
            },
        })
        # Check the hash that is used to confirm the user's data in the GET parameter is correct
        secret_key = settings.THIRD_PARTY_AUTH_CUSTOM_AUTH_FORMS['custom1']['secret_key']
        hmac_expected = hmac.new(secret_key, msg=data_decoded, digestmod=hashlib.sha256).digest()
        self.assertEqual(base64.b64decode(response.context['hmac']), hmac_expected)

        # Now our custom registration form creates or logs in the user:
        email, password = data_parsed['user_details']['email'], 'random_password'
        created_user = UserFactory(email=email, password=password)
        login_response = self.client.post(reverse('login'), {'email': email, 'password': password})
        self.assertEqual(login_response.status_code, 200)

        # Now our custom login/registration page must resume the pipeline:
        response = self.client.get(complete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/misc/final-destination')

        _, strategy = self.get_request_and_strategy()
        self.assert_social_auth_exists_for_user(created_user, strategy)

    def test_custom_form_error(self):
        """
        Use the Google provider to test the custom login/register failure redirects.
        """
        # The pipeline starts by a user GETting /auth/login/google-oauth2/?auth_entry=custom1
        # Synthesize that request and check that it redirects to the correct
        # provider page.
        auth_entry = 'custom1'  # See definition in lms/envs/test.py
        login_url = pipeline.get_login_url(self.provider.provider_id, auth_entry)
        login_url += "&next=/misc/final-destination"
        self.assert_redirect_to_provider_looks_correct(self.client.get(login_url))

        def fake_auth_complete_error(_inst, *_args, **_kwargs):
            """ Mock the backend's auth_complete() method """
            raise AuthException("Mock login failed")

        # Next, the provider makes a request against /auth/complete/<provider>.
        complete_url = pipeline.get_complete_url(self.provider.backend_name)
        with patch.object(self.provider.backend_class, 'auth_complete', fake_auth_complete_error):
            response = self.client.get(complete_url)
        # This should redirect to the custom error URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/misc/my-custom-sso-error-page')
