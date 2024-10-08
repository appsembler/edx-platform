"""
Tests for helpers.
"""
import pytest
from django.contrib.auth import get_user_model
from unittest.mock import patch
from django.test.client import RequestFactory

from ..helpers import is_preview_mode, PREVIEW_GET_PARAM


User = get_user_model()


def test_no_request():
    assert not is_preview_mode(), 'default to non-preview if no request is provided'


def test_request_non_preview_mode():
    request = RequestFactory().get('/test')
    request.user = User()
    assert not is_preview_mode(current_request=request), 'default to non-preview'


@pytest.mark.parametrize('preview_param', [True, 'true', 'True'])
def test_request_preview_mode_case_insensitive(preview_param):
    request = RequestFactory().get('/test', data={'preview': preview_param})
    request.user = User()
    is_preview_result = is_preview_mode(current_request=request)
    assert is_preview_result, 'Should respect case-insensitive `preview=true` param'


def test_request_preview_mode_without_user():
    request = RequestFactory().get('/test', data={'preview': 'true'})
    is_preview_result = is_preview_mode(current_request=request)
    assert not is_preview_result, 'Disable preview mode for unauthenticated users'


def test_request_preview_mode_crum():
    """
    Ensure `crum.get_current_request` is used when no request is provided via parameters.
    """
    request = RequestFactory().get('/test', data={PREVIEW_GET_PARAM: 'true'})
    request.user = User()
    with patch('crum.get_current_request', return_value=request):
        assert is_preview_mode(), 'Should default to `crum` request'


def test_request_preview_mode_test_yes():
    """
    Ensure `crum.get_current_request` should be `live` if provided anything other than yes.
    """
    request = RequestFactory().get('/test', data={PREVIEW_GET_PARAM: 'yes'})
    request.user = User()
    assert not is_preview_mode(current_request=request), 'Anything is falsy, except for `true`'
