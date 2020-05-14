"""
Waffle switches for credential_criteria Django app
"""
from openedx.core.djangoapps.waffle_utils import WaffleSwitchNamespace

# Namespace
WAFFLE_NAMESPACE = u'credential_criteria'

# Switches
WAFFLE_SWITCHES = WaffleSwitchNamespace(name=WAFFLE_NAMESPACE)


# Full name: credential_criteria.enable_credential_criteria_app
# Indicates whether or not to use the credential criteria functionality
# regardless of it being an installed app.
ENABLE_CREDENTIAL_CRITERIA_APP = u'enable_credential_criteria_app'
