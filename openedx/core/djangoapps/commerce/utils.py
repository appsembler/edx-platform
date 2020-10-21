""" Commerce API Service. """
from django.conf import settings
from edx_rest_api_client.client import EdxRestApiClient

from eventtracking import tracker
from openedx.core.djangoapps.oauth_dispatch.jwt import create_jwt_for_user
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


ECOMMERCE_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def create_tracking_context(user):
    """ Assembles attributes from user and request objects to be sent along
    in E-Commerce API calls for tracking purposes. """
    context_tracker = tracker.get_tracker().resolve_context()

    return {
        'lms_user_id': user.id,
        'lms_client_id': context_tracker.get('client_id'),
        'lms_ip': context_tracker.get('ip'),
    }


def is_commerce_service_configured():
    """
    Return a Boolean indicating whether or not configuration is present to use the external commerce service.
    """
    ecommerce_api_url = configuration_helpers.get_value('ECOMMERCE_API_URL', settings.ECOMMERCE_API_URL)
    return bool(ecommerce_api_url)


def ecommerce_api_client(user, session=None):
    """ Returns an E-Commerce API client setup with authentication for the specified user. """
    claims = {'tracking_context': create_tracking_context(user)}
    jwt = create_jwt_for_user(user, additional_claims=claims)

    return EdxRestApiClient(
        configuration_helpers.get_value('ECOMMERCE_API_URL', settings.ECOMMERCE_API_URL),
        jwt=jwt,
        session=session
    )
