"""
Helper module for Tahoe Auth0.

 - https://github.com/appsembler/tahoe-auth0/
"""
from django.conf import settings

from site_config_client.openedx import api as config_client_api

TAHOE_AUTH0_BACKEND_NAME = 'tahoe-auth0'


def is_tahoe_auth0_enabled():
    """
    Tahoe: Check if tahoe-auth0 package is enabled for the current site (or cluster-wide).
    """
    global_flag = settings.FEATURES.get('ENABLE_TAHOE_AUTH0', False)
    return config_client_api.get_admin_value('ENABLE_TAHOE_AUTH0', default=global_flag)
