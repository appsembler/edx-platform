"""
Common environment plugin settings for credential_criteria Django app.
"""

def plugin_settings(settings):
    settings.CREDENTIAL_CRITERIA_ROUTING_KEY = settings.CREDENTIALS_GENERATION_ROUTING_KEY
