"""
Common environment plugin settings for credential_criteria Django app.
"""


def plugin_settings(settings):
    settings.CREDENTIAL_CRITERIA_ROUTING_KEY = settings.CREDENTIALS_GENERATION_ROUTING_KEY

    # only these types can be used for criterion
    settings.CREDENTIAL_CONFERRING_BLOCK_TYPES = {'course', 'chapter', }
