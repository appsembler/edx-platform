"""
Waffle switches for credential_criteria Django app
"""
import waffle

from openedx.core.djangoapps.waffle_utils import WaffleSwitchNamespace

# Namespace
WAFFLE_NAMESPACE = u'credential_criteria'

# Switches

# Full name: credential_criteria.enable_credential_criteria_app
# Indicates whether or not to use the credential criteria functionality
# regardless of it being an installed app.
ENABLE_CREDENTIAL_CRITERIA_APP = u'enable_credential_criteria_app'


def waffle():
    """
    Returns the namespaced, cached, audited shared Waffle Switch class.
    """
    return WaffleSwitchNamespace(name=WAFFLE_NAMESPACE, log_prefix=u'Credential Criteria: ')


def credentential_criteria_is_active():
    """
    Check whether the feature switch is active.
    """
    return waffle.switch_is_active(ENABLE_CREDENTIAL_CRITERIA_APP)
