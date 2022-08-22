'''
Tests for multi-tenant cache APIs.
'''
import pytest
from datetime import datetime

from django.test import TestCase, override_settings


class MultiTenantCacheTestCase(TestCase):
    def setUp(self):
        super().setUp()
        with self.settings(CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
            'general': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        }):
            from openedx.core.djangoapps.appsembler.multi_tenant_cache import api
            self.cache = api.cache
            self.api = api

    def test_update_time_cache_key(self):
        key = self.api.build_tahoe_config_update_time_cache_key('omardo.com')
        assert key == 'tahoe_config_update:omardo.com'

    def test_clear_tahoe_site_cache(self):
        site_domain = 'arabicmath.org'
        key = self.api.build_tahoe_config_update_time_cache_key(site_domain)
        assert not self.cache.get(key, None), 'new domain, no cache entry is expected'

        now = datetime(2022, 8, 20, 7, 46, 22)
        last_update = self.api.clear_tahoe_site_cache(site_domain, now=now)
        assert last_update == '2022-08-20 07:46:22'

        assert self.cache.get(key, None) == last_update, 'Should set the last update in cache'
