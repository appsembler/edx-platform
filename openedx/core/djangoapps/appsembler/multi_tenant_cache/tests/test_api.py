"""
Tests for multi-tenant cache APIs.
"""
import pytest
from datetime import datetime
from django.core.cache.backends.locmem import LocMemCache


@pytest.fixture
def api_module(monkeypatch):
    from openedx.core.djangoapps.appsembler.multi_tenant_cache import api
    monkeypatch.setattr(api, 'cache', LocMemCache('mock', {}))
    return api


def test_update_time_cache_key(api_module):
    key = api_module.build_tahoe_config_update_time_cache_key('omardo.com')
    assert key == 'tahoe_config_update:omardo.com'


def test_clear_tahoe_site_cache(api_module):
    site_domain = 'arabicmath.org'
    key = api_module.build_tahoe_config_update_time_cache_key(site_domain)
    assert not api_module.cache.get(key), 'new domain, no cache entry is expected'

    now = datetime(2022, 8, 20, 7, 46, 22)
    last_update = api_module.clear_tahoe_site_cache(site_domain, now=now)
    assert last_update == '2022-08-20 07:46:22'

    assert api_module.cache.get(key) == last_update, 'Should set the last update in cache'
