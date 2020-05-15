"""
utility methods for credentials_criteria Django app.
"""

from django.conf import settings

from openedx.core.djangoapps.site_configuration.helpers import get_value

from . import waffle


def feature_is_enabled():
    """
    Return True or False based on whether waffle switch for feature is enabled.
    """
    return waffle.WAFFLE_SWITCHES.is_enabled(waffle.ENABLE_CREDENTIAL_CRITERIA_APP)


def block_can_confer_credentials(block_key):
    """
    Check whether this block is of a type that can confer a credential.
    """
    conferrable_block_types = get_value(
        "CREDENTIAL_CONFERRING_BLOCK_TYPES",
        settings.CREDENTIAL_CONFERRING_BLOCK_TYPES)
    return block_key.block_type in conferrable_block_types
