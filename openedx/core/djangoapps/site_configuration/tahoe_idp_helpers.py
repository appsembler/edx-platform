"""
Helper module for Tahoe Identity Provider package.

 - https://github.com/appsembler/tahoe-idp/
"""

from django.conf import settings
from django.urls import reverse

from site_config_client.openedx import api as config_client_api

from common.djangoapps import third_party_auth

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


def get_idp_form_url(request, initial_form_mode, next_url):
    """
    Get the login/register URLs for the identity provider.

    Disable upstream login/register forms when the Tahoe Identity Provider is enabled.
    """
    if not is_tahoe_idp_enabled():
        return None

    if not third_party_auth.is_enabled():
        return None

    has_running_pipeline = bool(third_party_auth.pipeline.get(request))
    if initial_form_mode == "register":
        if has_running_pipeline:
            # Upon registration, the form is displayed hidden for auto-submit.
            # Returning, None to avoid redirecting an otherwise needed form submit.
            return None

        return get_idp_register_url(next_url=next_url)
    else:
        return get_idp_login_url(next_url=next_url)
