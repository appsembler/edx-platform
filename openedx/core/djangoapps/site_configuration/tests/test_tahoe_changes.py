"""
Tests for site configuration's Tahoe customizations.
"""
import logging
import pytest
from sass import CompileError
from unittest.mock import patch, Mock

import ddt
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.utils import override_settings

from openedx.core.djangoapps.appsembler.sites.waffle import ENABLE_CONFIG_VALUES_MODIFIER
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from openedx.core.djangoapps.site_configuration.tests.factories import SiteConfigurationFactory


def ddt_without_and_with_modifier(test_func):
    """
    Decorator to pass `use_modifier` parameter.
    """
    test_func = ddt.data({
        'use_modifier': False,
    }, {
        'use_modifier': True,
    })(test_func)

    test_func = ddt.unpack(test_func)
    return test_func


@pytest.fixture
def clean_site_configuration_factory():
    """
    A factory to create site configuration in prep for `sass_variables` hack cleanup.
    """

    def internal_site_configuration_factory(**kwargs):
        initial_params = {
            'site_values': {'css_overrides_file': 'omar.css'},
        }

        if hasattr(SiteConfiguration, 'sass_variables'):
            # TODO: Clean up Site Configuration hacks: https://github.com/appsembler/edx-platform/issues/329
            initial_params = {
                'sass_variables': {},
                'page_elements': {},
            }

        initial_params.update(kwargs)
        site_config = SiteConfigurationFactory.build(**initial_params)
        return site_config
    return internal_site_configuration_factory


@override_settings(
    ENABLE_COMPREHENSIVE_THEMING=True,
    DEFAULT_SITE_THEME='edx-theme-codebase',
)
@ddt.ddt
class SiteConfigurationTests(TestCase):
    """
    Tests for SiteConfiguration and its signals/receivers.
    """
    domain = 'example-site.tahoe.appsembler.com'
    name = 'Example Tahoe Site'

    test_config = {
        "university": "Tahoe University",
        "platform_name": name,
        "SITE_NAME": domain,
        "course_org_filter": "TahoeX",
        "ENABLE_MKTG_SITE": False,
        "ENABLE_THIRD_PARTY_AUTH": False,
        "course_about_show_social_links": False,
    }

    @classmethod
    def setUpClass(cls):
        super(SiteConfigurationTests, cls).setUpClass()
        cls.site, _ = Site.objects.get_or_create(
            domain=cls.test_config['SITE_NAME'],
            name=cls.test_config['SITE_NAME'],
        )

        cls.scheme = urlsplit(settings.LMS_ROOT_URL).scheme
        cls.expected_site_root_url = '{scheme}://{domain}'.format(
            scheme=cls.scheme, domain=cls.domain)

    @ddt_without_and_with_modifier
    def test_site_configuration_compile_sass_on_save(self, use_modifier):
        """
        Test compile_microsite_sass with and without the TahoeConfigurationValueModifier.
        """
        with ENABLE_CONFIG_VALUES_MODIFIER.override(use_modifier):
            # add SiteConfiguration to database
            site_configuration = SiteConfigurationFactory.build(
                site=self.site,
            )

            site_configuration.save()  # Should not throw an exception

    @ddt_without_and_with_modifier
    def test_get_value(self, use_modifier):
        """
        Test that get_value returns correct value for Tahoe custom keys.
        """
        # add SiteConfiguration to database
        with ENABLE_CONFIG_VALUES_MODIFIER.override(use_modifier):
            site_configuration = SiteConfigurationFactory.create(
                site=self.site,
                site_values=self.test_config
            )
            assert bool(site_configuration.tahoe_config_modifier) == use_modifier, 'Sanity check for `override()`'

        # Make sure entry is saved and retrieved correctly
        self.assertEqual(site_configuration.get_value("PLATFORM_NAME"),
                         self.test_config['platform_name'])
        self.assertEqual(site_configuration.get_value("LMS_ROOT_URL"),
                         self.expected_site_root_url)
        self.assertTrue(site_configuration.get_value('ACTIVATION_EMAIL_SUPPORT_LINK'))
        self.assertTrue(site_configuration.get_value('ACTIVATION_EMAIL_SUPPORT_LINK').endswith('/help'))
        self.assertTrue(site_configuration.get_value('PASSWORD_RESET_SUPPORT_LINK'))
        self.assertTrue(site_configuration.get_value('PASSWORD_RESET_SUPPORT_LINK').endswith('/help'))

    @ddt_without_and_with_modifier
    def test_hardcoded_values_for_unsaved_config_instance(self, use_modifier):
        """
        If a SiteConfiguration has no site yet, the `get_value` will work safely.
        """
        with ENABLE_CONFIG_VALUES_MODIFIER.override(use_modifier):
            site_config = SiteConfiguration(enabled=True)

        assert site_config.get_value('SITE_NAME') is None
        assert site_config.get_value('SITE_NAME', 'test.com') == 'test.com'

    def test_hardcoded_values_for_config_instance_with_site_without_modifier(self):
        """
        If a SiteConfiguration has a site the `get_value` should return the right one.

        with ENABLE_CONFIG_VALUES_MODIFIER disabled.
        """
        with ENABLE_CONFIG_VALUES_MODIFIER.override(False):
            site = Site.objects.create(domain='my-site.com')
            site_config = SiteConfiguration(enabled=True, site=site)
            site_config.save()
            assert site_config.get_value('SITE_NAME', 'test.com') == 'my-site.com'

    def test_hardcoded_values_for_config_instance_with_site_with_modifier(self):
        """
        If a SiteConfiguration has a site the `get_value` should return the right one.

        with ENABLE_CONFIG_VALUES_MODIFIER enabled.
        """
        with ENABLE_CONFIG_VALUES_MODIFIER.override(True):
            site = Site.objects.create(domain='my-site.com')
            site_config = SiteConfiguration(enabled=True, site=site)  # No need to save for the value modifier to work
            assert site_config.get_value('SITE_NAME', 'test.com') == 'my-site.com'

    @ddt_without_and_with_modifier
    def test_get_value_for_org(self, use_modifier):
        """
        Test that get_value_for_org returns correct value for Tahoe custom keys.
        """
        with ENABLE_CONFIG_VALUES_MODIFIER.override(use_modifier):
            # add SiteConfiguration to database
            site_config = SiteConfigurationFactory.create(
                site=self.site,
                site_values=self.test_config
            )
            site_config.save()

            # Test that LMS_ROOT_URL is assigned to the SiteConfiguration on creation
            tahoex_org_name = self.test_config['course_org_filter']
            assert SiteConfiguration.get_value_for_org(tahoex_org_name, 'LMS_ROOT_URL') == self.expected_site_root_url


@pytest.mark.django_db
@patch('openedx.core.djangoapps.appsembler.sites.utils.compile_sass', Mock(return_value='I am working CSS'))
def test_logs_of_site_configuration_compile_sass_successful_on_save(caplog):
    """
    Test compile_microsite_sass successful logs.
    """
    caplog.set_level(logging.INFO)
    assert 'Sass compile' not in caplog.text
    SiteConfigurationFactory.create(site_values={'css_overrides_file': 'omar.css'})
    assert 'tahoe sass compiled successfully' in caplog.text, 'Should compile sass on save'


@pytest.mark.django_db
@patch('openedx.core.djangoapps.appsembler.sites.utils.compile_sass',
       Mock(side_effect=CompileError('CSS is not working -- Omar')))
def test_site_configuration_compile_sass_on_save_fail_gracefully(caplog, clean_site_configuration_factory):
    """
    Ensure save() is successful on sass compile errors.
    """
    caplog.set_level(logging.INFO)
    site_config = clean_site_configuration_factory(
        site=Site.objects.create(domain='test.com'),
        site_values={'css_overrides_file': 'omar.css'}
    )
    site_config.save()
    assert 'CSS is not working -- Omar' in caplog.text, 'Should log failures instead of throwing an exception'


@pytest.mark.django_db
def test_site_configuration_compile_sass_missing_override_file(caplog, clean_site_configuration_factory):
    """
    Ensure save() is successful on sass compile errors.
    """
    caplog.set_level(logging.INFO)
    site_config = clean_site_configuration_factory(
        site=Site.objects.create(domain='test.com'),
    )
    sass_status = site_config.compile_microsite_sass()
    assert not sass_status['successful_sass_compile'], 'Should fail due to missing css_overrides_file'
    assert 'Skipped compiling due to missing `css_overrides_file`' == sass_status['sass_compile_message']
    assert 'missing `css_overrides_file`' in caplog.text, 'Should log failures instead of throwing an exception'


@pytest.mark.django_db
@patch('openedx.core.djangoapps.appsembler.sites.utils.compile_sass',
       Mock(side_effect=CompileError('CSS is not working -- Omar')))
def test_site_configuration_compile_sass_failure(caplog, clean_site_configuration_factory):
    """
    Test sass status returns on failure.
    """
    caplog.set_level(logging.INFO)
    site_configuration = clean_site_configuration_factory(
        site_values={'css_overrides_file': 'omar.css'}
    )
    sass_status = site_configuration.compile_microsite_sass()
    assert not sass_status['successful_sass_compile']
    assert 'CSS is not working -- Omar' in sass_status['sass_compile_message']


@pytest.mark.django_db
@patch('openedx.core.djangoapps.appsembler.sites.utils.compile_sass', Mock(return_value='I am working CSS'))
def test_site_configuration_compile_sass_success(caplog, clean_site_configuration_factory):
    """
    Test sass status returns on success.
    """
    caplog.set_level(logging.INFO)
    site_configuration = clean_site_configuration_factory(
        site_values={'css_overrides_file': 'omar.css'}
    )
    sass_status = site_configuration.compile_microsite_sass()
    assert sass_status['successful_sass_compile']
    assert 'Sass compile finished successfully' in sass_status['sass_compile_message']


@override_settings(
    ENABLE_COMPREHENSIVE_THEMING=True,
)
class SiteConfigAPIClientTests(TestCase):
    """
    Tests for SiteConfiguration and its signals/receivers.
    """
    domain = 'example-site.tahoe.appsembler.com'
    name = 'API Adapter Platform'

    test_config = {
        "university": "Tahoe University",
        "platform_name": name,
        "SITE_NAME": domain,
        "course_org_filter": "TahoeX",
        "ENABLE_MKTG_SITE": False,
        "ENABLE_THIRD_PARTY_AUTH": False,
        "course_about_show_social_links": False,
    }

    sass_variables = [
        ["$brand-primary-color", ["#0090C1", "#0090C1"]],
        ["$brand-accent-color", ["#7f8c8d", "#7f8c8d"]],
    ]

    about_page = {
        'title': 'About page from site configuration service',
    }

    @classmethod
    def setUpClass(cls):
        super(SiteConfigAPIClientTests, cls).setUpClass()
        cls.site, _ = Site.objects.get_or_create(
            domain=cls.test_config['SITE_NAME'],
            name=cls.test_config['SITE_NAME'],
        )
        cls.api_adapter = Mock(
            get_value=cls.test_config.get,
            get_amc_v1_theme_css_variables=Mock(return_value=cls.sass_variables),
            get_amc_v1_page=Mock(return_value=cls.about_page),
        )

    def test_get_value_with_adapter(self):
        """
        Ensure api_adapter is used for `get_value()`.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={},
        )
        site_configuration.api_adapter = self.api_adapter
        site_configuration.save()
        assert site_configuration.get_value('platform_name') == 'API Adapter Platform'

    def test_formatted_sass_variables_with_adapter(self):
        """
        Ensure api_adapter is used for `_formatted_sass_variables()`.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={},
        )
        site_configuration.api_adapter = self.api_adapter
        assert site_configuration._formatted_sass_variables()

    def test_page_content_without_adapter(self):
        """
        Test `get_page_content()` without the SiteConfig adapter.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            page_elements={
                'about': {
                    'title': 'About page in Django model.',
                },
            },
        )
        assert site_configuration.get_page_content('about') == {
            'title': 'About page in Django model.',
        }

    def test_page_content_with_adapter(self):
        """
        Ensure `get_page_content()` uses the SiteConfig adapter when available.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            page_elements={
                'about': {
                    'title': 'About page in Django model.',
                },
            },
        )
        site_configuration.api_adapter = self.api_adapter
        assert site_configuration.get_page_content('about') == {
            'title': 'About page from site configuration service',
        }
