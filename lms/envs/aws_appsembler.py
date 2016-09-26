# aws_appsembler.py

from .aws import *
from .appsembler import *

INSTALLED_APPS += ('appsembler',)
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

TPA_CLEAN_USERNAMES_KEEP_DOMAIN_PART = ENV_TOKENS.get('TPA_CLEAN_USERNAMES_KEEP_DOMAIN_PART', False)
TPA_CLEAN_USERNAMES_REPLACER_CHAR = ENV_TOKENS.get('TPA_CLEAN_USERNAMES_REPLACER_CHAR', "")
TPA_CLEAN_USERNAMES_ADD_RANDOM_INT = ENV_TOKENS.get('TPA_CLEAN_USERNAMES_ADD_RANDOM_INT', False)