"""
Helper module for Tahoe Identity Provider package.

 - https://github.com/appsembler/tahoe-idp/
"""

from django.conf import settings

from site_config_client.openedx import api as config_client_api


def is_tahoe_idp_enabled(site_configuration=None):
    """
    Tahoe: Check if tahoe-idp package is enabled for the current site (or cluster-wide).

    :param site_configuration: specify a site_configuration rather than trying to get the one related to
        the current site. This helps with studio since the current site is always main site
    :return: boolean
    """
    return config_client_api.get_admin_value(
        'ENABLE_TAHOE_IDP',
        default=settings.FEATURES.get('ENABLE_TAHOE_IDP', False),  # the global flag
        site_configuration=site_configuration,
    )
