# devstack_appsembler.py

import os

from .devstack import *
from .appsembler import *


if FEATURES.get('ENABLE_TAXOMAN', False):
    try:
        # Just a check, we don't need it for the settings
        import taxoman_api
        # We need this for webpack loader
        import taxoman.settings
        TAXOMAN_ENABLED = True
    except ImportError:
        TAXOMAN_ENABLED = False
else:
    TAXOMAN_ENABLED = False


ENV_APPSEMBLER_FEATURES = ENV_TOKENS.get('APPSEMBLER_FEATURES', {})
for feature, value in ENV_APPSEMBLER_FEATURES.items():
    APPSEMBLER_FEATURES[feature] = value

# disable caching in dev environment
for cache_key in CACHES.keys():
    CACHES[cache_key]['BACKEND'] = 'django.core.cache.backends.dummy.DummyCache'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

INSTALLED_APPS += (
    'appsembler',
    'appsembler_api'
)

DEFAULT_TEMPLATE_ENGINE['OPTIONS']['context_processors'] += ('appsembler.context_processors.intercom',)

CUSTOM_LOGOUT_REDIRECT_URL = ENV_TOKENS.get('CUSTOM_LOGOUT_REDIRECT_URL', '/')

TPA_CLEAN_USERNAMES_KEEP_DOMAIN_PART = ENV_TOKENS.get('TPA_CLEAN_USERNAMES_KEEP_DOMAIN_PART', False)
TPA_CLEAN_USERNAMES_REPLACER_CHAR = ENV_TOKENS.get('TPA_CLEAN_USERNAMES_REPLACER_CHAR', "")
TPA_CLEAN_USERNAMES_ADD_RANDOM_INT = ENV_TOKENS.get('TPA_CLEAN_USERNAMES_ADD_RANDOM_INT', False)

if APPSEMBLER_FEATURES.get('ENABLE_EXTERNAL_COURSES', False):
    INSTALLED_APPS += (
        'openedx.core.djangoapps.appsembler.external_courses',
    )

EDX_ORG_COURSE_API_URL = ENV_TOKENS.get('EDX_ORG_COURSE_API_URL', False)
EDX_ORG_COURSE_API_TOKEN_URL = AUTH_TOKENS.get('EDX_ORG_COURSE_API_TOKEN_URL', False)
EDX_ORG_COURSE_API_CLIENT_ID = AUTH_TOKENS.get('EDX_ORG_COURSE_API_CLIENT_ID', False)
EDX_ORG_COURSE_API_CLIENT_SECRET = AUTH_TOKENS.get('EDX_ORG_COURSE_API_CLIENT_SECRET', False)
EDX_ORG_COURSE_API_TOKEN_TYPE = AUTH_TOKENS.get('EDX_ORG_COURSE_API_TOKEN_TYPE', False)
EDX_ORG_COURSE_API_CATALOG_IDS = ENV_TOKENS.get('EDX_ORG_COURSE_API_CATALOG_IDS', False)

if APPSEMBLER_FEATURES.get('ENABLE_EXTERNAL_COURSES', False):
    if ENV_TOKENS.get('EXTERNAL_COURSES_FETCH_PERIOD_HOURS', 24) is not None:
        CELERYBEAT_SCHEDULE['fetch-external-courses'] = {
            'task': 'openedx.core.djangoapps.appsembler.external_courses.tasks.fetch_courses',
            'schedule': datetime.timedelta(
                hours=ENV_TOKENS.get('EXTERNAL_COURSES_FETCH_PERIOD_HOURS', 24)
            ),
        }

if (APPSEMBLER_FEATURES.get('ENABLE_USAGE_TRACKING', False) or
        APPSEMBLER_FEATURES.get('ENABLE_USAGE_AGGREGATION', False)):
    # enable both apps for either feature flag, because
    #
    # * appsembler_usage depends on souvenirs models
    #
    # * appsembler_usage adds backfill_usage and email_usage management
    #   commands even if the aggregation DB isn't available.
    #
    INSTALLED_APPS += (
        'souvenirs',
        'openedx.core.djangoapps.appsembler.usage',  # appsembler_usage
    )

    if APPSEMBLER_FEATURES.get('ENABLE_USAGE_TRACKING', False):
        # enable live usage tracking via middleware
        MIDDLEWARE_CLASSES += (
            'souvenirs.middleware.SouvenirsMiddleware',
        )

    # router to send aggregation to cloud sql.
    # this should be enabled even if the aggregation DB isn't available,
    # to avoid trying to run migrations or store aggregation data in MySQL.
    DATABASE_ROUTERS += [
        'openedx.core.djangoapps.appsembler.usage.routers.AppsemblerUsageRouter',
    ]

    # appsembler devstack has dummy caches, but souvenirs needs a real cache
    # for rate-limiting writes to DB.
    SOUVENIRS_CACHE_NAME = 'souvenirs'
    CACHES[SOUVENIRS_CACHE_NAME] = {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'souvenirs',
    }

    # operator can override DB auth for migrations
    if ('appsembler_usage' in DATABASES and
            os.environ.get('APPSEMBLER_USAGE_DB_AUTH')):
        _user, _password = os.environ['APPSEMBLER_USAGE_DB_AUTH'].split(':', 1)
        DATABASES['appsembler_usage'].update({
            'USER': _user,
            'PASSWORD': _password,
        })

    # custom reports function to count learners, staff, etc.
    SOUVENIRS_USAGE_REPORTS_FUNCTION = 'openedx.core.djangoapps.appsembler.usage.reports.usage_for_periods'

elif 'appsembler_usage' in DATABASES:
    # if the AppsemblerUsageRouter isn't enabled, then avoid mistakes by
    # removing the database alias
    del DATABASES['appsembler_usage']

CUSTOM_SSO_FIELDS_SYNC = ENV_TOKENS.get('CUSTOM_SSO_FIELDS_SYNC', {})
# to allow to run python-saml with custom port
SP_SAML_RESTRICT_MODE = False

#configure auth backends
if 'LMS_AUTHENTICATION_BACKENDS' in APPSEMBLER_FEATURES.keys():
    #default behavior is to replace the existing backends with those in APPSEMBLER_FEATURES
    AUTHENTICATION_BACKENDS = tuple(APPSEMBLER_FEATURES['LMS_AUTHENTICATION_BACKENDS'])

EXCLUSIVE_SSO_LOGISTRATION_URL_MAP = ENV_TOKENS.get('EXCLUSIVE_SSO_LOGISTRATION_URL_MAP', {})

#attempt to import model from our custom fork of edx-organizations
# if it works, then also add the middleware
try:
    from organizations.models import UserOrganizationMapping
    MIDDLEWARE_CLASSES += (
        'organizations.middleware.OrganizationMiddleware',
    )
except ImportError:
    pass

##### Third-party auth options ################################################
if FEATURES.get('ENABLE_THIRD_PARTY_AUTH'):
    SOCIAL_AUTH_OAUTH_EXTRA_SETTINGS = AUTH_TOKENS.get('SOCIAL_AUTH_OAUTH_EXTRA_SETTINGS', {})

# override devstack.py automatic enabling of courseware discovery
FEATURES['ENABLE_COURSE_DISCOVERY'] = ENV_TOKENS['FEATURES'].get('ENABLE_COURSE_DISCOVERY', FEATURES['ENABLE_COURSE_DISCOVERY'])

if TAXOMAN_ENABLED:
    WEBPACK_LOADER['TAXOMAN_APP'] = {
        'BUNDLE_DIR_NAME': taxoman.settings.bundle_dir_name,
        'STATS_FILE': taxoman.settings.stats_file,
    }