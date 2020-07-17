"""
Settings for Appsembler on production (aka AWS), both LMS and CMS.
"""

import dj_database_url
from django.utils.translation import ugettext_lazy as _


def plugin_settings(settings):
    """
    Appsembler overrides for both production AND devstack.

    Make sure those are compatible for devstack via defensive coding.

    This file, however, won't run in test environments.
    """
    settings.APPSEMBLER_FEATURES = settings.ENV_TOKENS.get('APPSEMBLER_FEATURES', settings.APPSEMBLER_FEATURES)
    settings.APPSEMBLER_AMC_API_BASE = settings.AUTH_TOKENS.get('APPSEMBLER_AMC_API_BASE')
    settings.APPSEMBLER_FIRST_LOGIN_API = '/logged_into_edx'

    settings.AMC_APP_URL = settings.ENV_TOKENS.get('AMC_APP_URL')

    settings.DEFAULT_COURSE_MODE_SLUG = settings.ENV_TOKENS.get('EDXAPP_DEFAULT_COURSE_MODE_SLUG', 'audit')
    settings.DEFAULT_MODE_NAME_FROM_SLUG = _(settings.DEFAULT_COURSE_MODE_SLUG.capitalize())

    settings.SEARCH_ENGINE = "search.elastic.ElasticSearchEngine"

    settings.INTERCOM_APP_ID = settings.AUTH_TOKENS.get("INTERCOM_APP_ID")
    settings.INTERCOM_APP_SECRET = settings.AUTH_TOKENS.get("INTERCOM_APP_SECRET")

    settings.GOOGLE_ANALYTICS_APP_ID = settings.AUTH_TOKENS.get('GOOGLE_ANALYTICS_APP_ID')
    settings.HUBSPOT_API_KEY = settings.AUTH_TOKENS.get('HUBSPOT_API_KEY')
    settings.HUBSPOT_PORTAL_ID = settings.AUTH_TOKENS.get('HUBSPOT_PORTAL_ID')
    settings.MIXPANEL_APP_ID = settings.AUTH_TOKENS.get('MIXPANEL_APP_ID')

    settings.MANDRILL_API_KEY = settings.AUTH_TOKENS.get("MANDRILL_API_KEY")
    if settings.MANDRILL_API_KEY:
        settings.EMAIL_BACKEND = settings.ENV_TOKENS.get('EMAIL_BACKEND', 'anymail.backends.mandrill.MandrillBackend')
        settings.ANYMAIL = {
            "MANDRILL_API_KEY": settings.MANDRILL_API_KEY,
        }
        settings.INSTALLED_APPS += ("anymail",)

    # Sentry
    settings.SENTRY_DSN = settings.AUTH_TOKENS.get('SENTRY_DSN', False)
    if settings.SENTRY_DSN:
        # Set your DSN value
        settings.RAVEN_CONFIG = {
            'environment': settings.FEATURES['ENVIRONMENT'],  # This should be moved somewhere more sensible
            'tags': {
                'app': 'edxapp',
            },
            'dsn': settings.SENTRY_DSN,
        }

        settings.INSTALLED_APPS += ('raven.contrib.django.raven_compat',)

    if settings.FEATURES.get('ENABLE_TIERS_APP', False):
        settings.TIERS_ORGANIZATION_MODEL = 'organizations.Organization'
        settings.TIERS_EXPIRED_REDIRECT_URL = settings.ENV_TOKENS.get('TIERS_EXPIRED_REDIRECT_URL', None)
        settings.TIERS_ORGANIZATION_TIER_GETTER_NAME = 'get_tier_for_org'

        settings.TIERS_DATABASE_URL = settings.AUTH_TOKENS.get('TIERS_DATABASE_URL')
        settings.DATABASES['tiers'] = dj_database_url.parse(settings.TIERS_DATABASE_URL)
        settings.DATABASE_ROUTERS += ['openedx.core.djangoapps.appsembler.sites.routers.TiersDbRouter']

        settings.MIDDLEWARE_CLASSES += (
            'tiers.middleware.TierMiddleware',
        )
        settings.INSTALLED_APPS += (
            'tiers',
        )
