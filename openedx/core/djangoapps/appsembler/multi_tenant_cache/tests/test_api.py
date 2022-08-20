"""
Tests for multi-tenant cache APIs.
"""
import pytest
from datetime import datetime


@pytest.fixture(autouse=True)
def locmem_cache(settings, ):
    settings.CACHES = {
        "general": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

    from django.core import cache

    local_cache = cache.caches['general']
    local_cache.clear()
    return local_cache


@pytest.fixture
def api_module():
    from openedx.core.djangoapps.appsembler.multi_tenant_cache import api
    return api


def test_update_time_cache_key(locmem_cache, api_module):
    key = api_module.build_tahoe_config_update_time_cache_key('omardo.com')
    assert key == 'tahoe_config_update:omardo.com'


def test_clear_tahoe_site_cache(locmem_cache, api_module):
    site_domain = 'arabicmath.org'
    key = api_module.build_tahoe_config_update_time_cache_key(site_domain)
    assert not locmem_cache.get(key), 'new domain, no cache entry is expected'

    now = datetime(2022, 8, 20, 7, 46, 22)
    last_update = api_module.clear_tahoe_site_cache(site_domain, now=now)
    assert last_update == '2022-08-20 07:46:22'

    assert locmem_cache.get(key) == last_update, 'Should set the last update in cache'
