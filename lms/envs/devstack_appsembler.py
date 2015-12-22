# devstack_appsembler.py

from .devstack import *
from .appsembler import *

INSTALLED_APPS += ('appsembler',)
TEMPLATE_CONTEXT_PROCESSORS += ('appsembler.context_processors.intercom',)

MIDDLEWARE_CLASSES = (
    'db_multitenant.middleware.MultiTenantMiddleware',
    'threadlocals.middleware.ThreadLocalMiddleware',
    ) + MIDDLEWARE_CLASSES

SOUTH_DATABASE_ADAPTERS = {
    'default': 'south.db.mysql'
}

MULTITENANT_MAPPER_CLASS = 'appsembler.mapper.SimpleTenantMapper'

DATABASES['default']['ENGINE'] = 'db_multitenant.db.backends.mysql'
