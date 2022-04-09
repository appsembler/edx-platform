"""
Helper module for Tahoe Identity Provider package.

 - https://github.com/appsembler/tahoe-idp/
"""

from django.conf import settings
from django.urls import reverse

from site_config_client.openedx import api as config_client_api

TAHOE_IDP_BACKEND_NAME = 'tahoe-idp'


def is_tahoe_idp_enabled():
    """
    Tahoe: Check if tahoe-idp package is enabled for the current site (or cluster-wide).
    """
    global_flag = settings.FEATURES.get('ENABLE_TAHOE_IDP', False)
    return config_client_api.get_admin_value('ENABLE_TAHOE_IDP', default=global_flag)


def build_next_qs(next_url, with_ampersand=False):
    """
    Builds a next URL querystring portion.
    """
    if next:
        return '{amp}next={next_url}'.format(
            next_url=next_url,
            amp='&' if with_ampersand else '',
        )

    return ''


def get_idp_login_url(next_url=None):
    """
    Get Auth0 login URL which uses `social_auth`.
    """
    return '{base}?auth_entry=login{next_qs}'.format(
        base=reverse('social:begin', args=[TAHOE_IDP_BACKEND_NAME]),
        next_qs=build_next_qs(next_url, with_ampersand=True),
    )


def get_idp_register_url(next_url=None):
    """
    Get Auth0 register URL which using `tahoe-idp` package.
    """
    return '{base}?{next_qs}'.format(
        base=reverse('tahoe_idp:register_view'),
        next_qs=build_next_qs(next_url, with_ampersand=False),
    )
