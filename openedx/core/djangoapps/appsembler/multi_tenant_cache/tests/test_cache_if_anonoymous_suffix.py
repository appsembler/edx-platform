"""
Integration tests for multi-tenant cache APIs with `cache_if_anonoymous.
"""
from unittest.mock import Mock, patch

from common.djangoapps.util import cache as cache_utils


def test_cache_if_anonymous_behaviour(locmem_cache, request_factory, response_factory):
    """
    Test basic behaviour for cache and clearing.
    """

    @cache_utils.cache_if_anonymous()
    def dummy_view(request):
        return response_factory(request.path)

    response = dummy_view(request_factory('/terms_of_service'))  # First call to terms_of_service page
    assert '/terms_of_service' in response.content.decode('utf-8')
    response_factory.assert_called_once_with('/terms_of_service')  # First call without cache

    response = dummy_view(request_factory('/terms_of_service'))  # Second call to terms_of_service page
    assert '/terms_of_service' in response.content.decode('utf-8')
    response_factory.assert_called_once_with('/terms_of_service')  # Should not call, use cache

    response = dummy_view(request_factory('/about'))  # First call to about page
    assert '/about' in response.content.decode('utf-8')
    response_factory.assert_called_with('/about')  # First call without cache


@patch('openedx.core.djangoapps.appsembler.multi_tenant_cache.api.time', Mock(return_value=1661140000.9315279))
def test_cache_if_anonymous_cache_key_suffix(locmem_cache, request_factory, response_factory):
    """
    Test internal cache suffix for `cache_if_anonymous`.
    """
    expected_cache_key = 'test.org.cache_if_anonymous.en./about:1661140000.9315279:'
    assert not locmem_cache.get(expected_cache_key), 'Should not be cached yet'

    @cache_utils.cache_if_anonymous()
    def dummy_view(request):
        return response_factory(request.path)

    response = dummy_view(request_factory('/about'))
    assert '/about' in response.content.decode('utf-8')

    assert locmem_cache.get(expected_cache_key), 'Page should be cached with timestamp'


@patch.dict('django.conf.settings.FEATURES', {'TAHOE_MULTI_TENANT_SITE_CACHE': False})
def test_disabled_cache_if_anonymous_cache_key_suffix(locmem_cache, request_factory, response_factory):
    """
    Test internal cache suffix for `cache_if_anonymous` if the feature is turned off.
    """
    expected_cache_key = 'test.org.cache_if_anonymous.en./about'
    assert not locmem_cache.get(expected_cache_key), 'Should not be cached yet'

    @cache_utils.cache_if_anonymous()
    def dummy_view(request):
        return response_factory(request.path)

    response = dummy_view(request_factory('/about'))
    assert '/about' in response.content.decode('utf-8')

    assert locmem_cache.get(expected_cache_key), 'Page should be cached without timestamp'
