"""
Fixtures for tests.
"""

import pytest

from django.core.cache.backends.locmem import LocMemCache

from openedx.core.djangoapps.appsembler.multi_tenant_cache import api as mte_cache_api
from common.djangoapps.util import cache as cache_utils
from django.contrib.sites.models import Site
from django.http import HttpResponse
from unittest.mock import Mock

from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser


@pytest.fixture
def locmem_cache(monkeypatch):
    """
    Use cleared LocMemCache for cache_if_anonymous and multi_tenant_cache modules.
    """
    mocked_cache = LocMemCache('mock', {})
    monkeypatch.setattr(mte_cache_api, 'cache', mocked_cache)
    monkeypatch.setattr(cache_utils, 'cache', mocked_cache)
    mocked_cache.clear()
    return mocked_cache


@pytest.fixture
def request_factory():
    def _request_factory(path):
        request = RequestFactory().get(path)
        request.site = Site(domain='test.org')
        request.user = AnonymousUser()
        request.META['HTTP_HOST'] = request.site.domain
        return request

    return _request_factory


@pytest.fixture
def response_factory():
    def get_new_response_with_path(path):
        return HttpResponse(str({'path': path}).encode('utf-8'))

    factory = Mock(side_effect=get_new_response_with_path)
    return factory
