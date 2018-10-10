# aws_appsembler.py

from .aws import *
from .appsembler import *

ENV_APPSEMBLER_FEATURES = ENV_TOKENS.get('APPSEMBLER_FEATURES', {})
for feature, value in ENV_APPSEMBLER_FEATURES.items():
    APPSEMBLER_FEATURES[feature] = value

INSTALLED_APPS += (
    'appsembler',
    'appsembler_api',
)

DEFAULT_TEMPLATE_ENGINE['OPTIONS']['context_processors'] += ('appsembler.context_processors.intercom',)

SEARCH_SKIP_ENROLLMENT_START_DATE_FILTERING = True

#enable course visibility feature flags
COURSE_CATALOG_VISIBILITY_PERMISSION = 'see_in_catalog'
COURSE_ABOUT_VISIBILITY_PERMISSION = 'see_about_page'

# SENTRY
SENTRY_DSN = AUTH_TOKENS.get('SENTRY_DSN', False)

if SENTRY_DSN:

    # Set your DSN value
    RAVEN_CONFIG = {
        'dsn': SENTRY_DSN,
    }

    INSTALLED_APPS += ('raven.contrib.django.raven_compat',)

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

if FEATURES.get('ENABLE_CORS_HEADERS', False):
    # This middleware class and setting allows to run cross requests when we are
    # under https, CORS headers requests external referers are blocked under
    # https, there is a new setting in Django 1.9, but until we upgrade to that
    # version we need to use this.
    # Docs: https://github.com/ottoyiu/django-cors-headers#cors_replace_https_referer
    CORS_REPLACE_HTTPS_REFERER = True

HTTPS = 'on' if ENV_TOKENS.get('BASE_SCHEME', 'https').lower() == 'https' else 'off'

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

# Enable Figures if it is included
if 'figures' in INSTALLED_APPS:
    import figures.settings
