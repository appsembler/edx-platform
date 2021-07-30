"""Tests the Appsembler Apps settings modules
"""

import pytest
from mock import patch

from openedx.core.djangoapps.theming.helpers_dirs import Theme

from openedx.core.djangoapps.appsembler.settings.settings import (
    devstack_cms,
    devstack_lms,
    production_cms,
    production_lms,
)


@pytest.fixture(scope='function')
def fake_production_settings(settings):
    """
    Pytest fixture to fake production settings such as AUTH_TOKENS that are otherwise missing in tests.
    """
    settings.AUTH_TOKENS = {}
    settings.CELERY_QUEUES = {}
    settings.ALTERNATE_QUEUE_ENVS = []
    settings.ENV_TOKENS = {
        'LMS_BASE': 'fake-lms-base',
        'LMS_ROOT_URL': 'fake-lms-root-url',
        'EMAIL_BACKEND': 'fake-email-backend',
        'FEATURES': {}
    }
    settings.MAIN_SITE_REDIRECT_WHITELIST = []
    return settings


def test_devstack_cms(fake_production_settings):
    devstack_cms.plugin_settings(fake_production_settings)


def test_devstack_lms(fake_production_settings):
    devstack_lms.plugin_settings(fake_production_settings)


def test_production_cms(fake_production_settings):
    production_cms.plugin_settings(fake_production_settings)


@pytest.mark.parametrize('retval, additional_count', [(False, 0), (True, 1)])
def test_production_lms(fake_production_settings, retval, additional_count):
    settings = fake_production_settings
    with patch('openedx.core.djangoapps.appsembler.settings.helpers.path.isdir',
               return_value=retval):
        with patch(
            'openedx.core.djangoapps.theming.helpers_dirs.get_themes_unchecked',
            return_value=[Theme('fake-theme', 'fake-theme', '.', '.')]
        ):
            expected_dir_len = len(settings.STATICFILES_DIRS) + additional_count
            production_lms.plugin_settings(settings)
            assert len(settings.STATICFILES_DIRS) == expected_dir_len
