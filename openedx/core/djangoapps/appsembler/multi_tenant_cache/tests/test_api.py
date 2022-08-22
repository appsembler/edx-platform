"""
Tests for multi-tenant cache APIs.
"""

from unittest.mock import patch

from django.contrib.sites.models import Site

from openedx.core.djangoapps.appsembler.multi_tenant_cache import api


def test_update_time_cache_key(locmem_cache):
    key = api.build_tahoe_config_update_time_cache_key('omardo.com')
    assert key == 'tahoe_config_update:omardo.com'


def test_clear_tahoe_site_cache_auto_now(locmem_cache):
    """
    Ensure `clear_tahoe_site_cache` uses `timezone.now()` by default.
    """
    assert api.clear_tahoe_site_cache('test.com'), 'Should return timestamp'


def test_clear_tahoe_site_cache(locmem_cache):
    """
    Ensure `clear_tahoe_site_cache` sets a fresh key.
    """
    site_domain = 'arabicmath.org'
    key = api.build_tahoe_config_update_time_cache_key(site_domain)
    assert not api.cache.get(key), 'new domain, no cache entry is expected'

    now = 1661140000.9315279
    last_update = api.clear_tahoe_site_cache(site_domain, now=now)
    assert last_update == '1661140000.9315279'

    assert api.cache.get(key) == last_update, 'Should set the last update in cache'

    now2 = 1661143333.9315279
    api.clear_tahoe_site_cache(site_domain, now=now2)
    assert api.cache.get(key) == str(now2), 'Should reset the cache key on request'


def test_get_tahoe_config_update_time(locmem_cache):
    config_update_time1 = api.get_tahoe_config_update_time('test.com')
    assert config_update_time1, 'Should return timestamp'

    config_update_time2 = api.get_tahoe_config_update_time('test.com')
    assert config_update_time1 == config_update_time2, 'Should preserve the time across calls unless cleared'


def test_suffix_tahoe_cache_key(locmem_cache, monkeypatch):
    """
    Test the suffix key.
    """
    site = Site(domain='omardo.com')
    now = 1661140000.9315279
    suffixed_key = api.suffix_tahoe_cache_key(site, 'page_cache:about_page', now=now)
    assert suffixed_key == 'page_cache:about_page:1661140000.9315279:', 'Should suffix key with update timestamp'


def test_suffix_tahoe_cache_key_no_domain(locmem_cache):
    """
    Test the suffix key.
    """
    with patch.object(api, 'build_tahoe_config_update_time_cache_key') as build_key_func:
        assert api.suffix_tahoe_cache_key(None, 'page_cache:about_page')
        build_key_func.assert_called_with('no_site')  # Should accept `None` argument

    with patch.object(api, 'build_tahoe_config_update_time_cache_key') as build_key_func:
        assert api.suffix_tahoe_cache_key(object(), 'page_cache:about_page')
        build_key_func.assert_called_with('no_site')  # Should accept site without domain
