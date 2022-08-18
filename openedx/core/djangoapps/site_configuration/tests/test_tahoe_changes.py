"""
Tests for site configuration's Tahoe customizations.
"""
from io import StringIO

import logging
import pytest
from sass import CompileError
from unittest.mock import patch, Mock

import ddt
from urllib.parse import urlsplit

from organizations.models import Organization
from organizations.tests.factories import OrganizationFactory

from django.conf import settings
from django.contrib.sites.models import Site
from django.test import TestCase
from django.test.utils import override_settings

from site_config_client.openedx.adapter import SiteConfigAdapter

from openedx.core.djangoapps.appsembler.multi_tenant_emails.tests.test_utils import with_organization_context
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from openedx.core.djangoapps.site_configuration.tests.factories import SiteConfigurationFactory
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers


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

    def test_site_configuration_compile_sass_on_save(self):
        """
        Test compile_microsite_sass
        """
        # add SiteConfiguration to database
        site_configuration = SiteConfigurationFactory.build(
            site=self.site,
        )

        site_configuration.save()  # Should not throw an exception

    def test_get_value(self):
        """
        Test that get_value returns correct value for Tahoe custom keys.
        """
        # add SiteConfiguration to database
        site_configuration = SiteConfigurationFactory.build(
            site=self.site,
            site_values=self.test_config
        )
        site_configuration.save()
        site_configuration.refresh_from_db()
        assert bool(site_configuration.tahoe_config_modifier), 'Sanity check for `override()`'

        # Make sure entry is saved and retrieved correctly
        assert site_configuration.get_value("PLATFORM_NAME") == self.test_config['platform_name']
        assert site_configuration.get_value("LMS_ROOT_URL") == self.expected_site_root_url
        assert site_configuration.get_value('ACTIVATION_EMAIL_SUPPORT_LINK')
        assert site_configuration.get_value('ACTIVATION_EMAIL_SUPPORT_LINK').endswith('/help')
        assert site_configuration.get_value('PASSWORD_RESET_SUPPORT_LINK')
        assert site_configuration.get_value('PASSWORD_RESET_SUPPORT_LINK').endswith('/help')

        site_configuration.site_values['platform_name'] = 'new platform name'
        site_configuration.save()
        site_configuration.refresh_from_db()
        assert site_configuration.get_value('platform_name') == 'new platform name'
        assert site_configuration.get_value('PLATFORM_NAME') == 'new platform name'

    def test_hardcoded_values_for_unsaved_config_instance(self):
        """
        If a SiteConfiguration has no site yet, the `get_value` will work safely.
        """
        site_config = SiteConfiguration(enabled=True)

        assert site_config.get_value('SITE_NAME') is None
        assert site_config.get_value('SITE_NAME', 'test.com') == 'test.com'

    def test_hardcoded_values_for_config_instance_with_site_with_modifier(self):
        """
        If a SiteConfiguration has a site the `get_value` should return the right one.
        """
        site = Site.objects.create(domain='my-site.com')
        site_config = SiteConfiguration(enabled=True, site=site)  # No need to save for the value modifier to work
        assert site_config.get_value('SITE_NAME', 'test.com') == 'my-site.com'

    def test_get_value_for_org(self):
        """
        Test that get_value_for_org returns correct value for Tahoe custom keys.
        """
        # add SiteConfiguration to database
        site_config = SiteConfigurationFactory.create(
            site=self.site,
            site_values=self.test_config
        )
        site_config.save()

        # Test that LMS_ROOT_URL is assigned to the SiteConfiguration on creation
        tahoex_org_name = self.test_config['course_org_filter']
        assert SiteConfiguration.get_value_for_org(tahoex_org_name, 'LMS_ROOT_URL') == self.expected_site_root_url

    def test_get_css_url_in_live_mode(self):
        site_config = SiteConfigurationFactory.create(site=self.site)
        assert site_config.get_css_url() == '/static/uploads/example-site.tahoe.appsembler.com.css'

    def test_get_css_url_in_preview_mode_missing_file(self):
        """
        Because the preview file isn't compiled, calling get_css_url(preview=True) should return the `live` file.
        """
        site_config = SiteConfigurationFactory.create(site=self.site)
        assert site_config.get_css_url(preview=True) == '/static/uploads/example-site.tahoe.appsembler.com.css'

    @patch('openedx.core.djangoapps.site_configuration.models.get_customer_themes_storage')
    def test_get_css_url_in_preview_existing_file(self, mock_get_storage):
        storage = Mock()
        storage.exists.return_value = True  # Act as if the file exists.
        storage.open.return_value = StringIO()
        storage.url = lambda filename: '/path/to/{}'.format(filename)
        mock_get_storage.return_value = storage
        site_config = SiteConfigurationFactory.create(site=self.site)
        assert site_config.get_css_url(preview=True) == '/path/to/preview-example-site.tahoe.appsembler.com.css'


@pytest.mark.django_db
@patch('openedx.core.djangoapps.appsembler.sites.utils.compile_sass', Mock(return_value='I am working CSS'))
def test_logs_of_site_configuration_compile_sass_successful_on_save(caplog):
    """
    Test compile_microsite_sass successful logs.
    """
    caplog.set_level(logging.INFO)
    assert 'Sass compile' not in caplog.text
    SiteConfigurationFactory.create(site_values={})
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
        site_values={},
    )
    site_config.save()
    assert 'CSS is not working -- Omar' in caplog.text, 'Should log failures instead of throwing an exception'


@pytest.mark.django_db
@patch('openedx.core.djangoapps.appsembler.sites.utils.compile_sass',
       Mock(side_effect=CompileError('CSS is not working -- Omar')))
def test_site_configuration_compile_sass_failure(caplog, clean_site_configuration_factory):
    """
    Test sass status returns on failure.
    """
    caplog.set_level(logging.INFO)
    site_configuration = clean_site_configuration_factory(site_values={})
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
    site_configuration = clean_site_configuration_factory(site_values={})
    sass_status = site_configuration.compile_microsite_sass()
    assert sass_status['successful_sass_compile']
    assert 'Sass compile finished successfully' in sass_status['sass_compile_message']
    assert 'main.scss' in sass_status['scss_file_used'], 'Should use the default file'
    assert '_main-v2.scss' not in sass_status['scss_file_used']


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

    sass_variables_v1 = [
        ["$brand-primary-color", ["#0090C1", "#0090C1"]],
        ["$brand-accent-color", ["#7f8c8d", "#7f8c8d"]],
    ]

    sass_variables_v2 = {
        'primary_brand_color': '#0090c1',
        'buttons_accents_color': '#0040f6',
    }

    backend_configs = {
        'configuration': {
            'page': {
                'about': {
                    'title': 'About page from site configuration service',
                }
            },
            'css': sass_variables_v2,
            'setting': {
                'THEME_VERSION': 'tahoe-v2',
                **test_config,
            },
            'secret': {
                'SEGMENT_KEY': 'test-secret-from-service',
            },
            'admin': {
                'IDP_TENANT_ID': 'dummy-tenant-id',
            }
        }
    }

    @classmethod
    def setUpClass(cls):
        super(SiteConfigAPIClientTests, cls).setUpClass()
        cls.site, _ = Site.objects.get_or_create(
            domain=cls.test_config['SITE_NAME'],
            name=cls.test_config['SITE_NAME'],
        )
        cls.api_adapter = SiteConfigAdapter('dummy-uuid')
        cls.api_adapter.get_backend_configs = Mock(return_value=cls.backend_configs)

    def test_get_value_with_adapter(self):
        """
        Ensure api_adapter is used for `get_value()`.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={},
        )
        site_configuration._api_adapter = self.api_adapter
        site_configuration.save()
        assert site_configuration.get_value('platform_name') == 'API Adapter Platform'

    def test_theme_v1_variables_overrides_without_adapter(self):
        """
        Ensure `_get_theme_v1_variables_overrides()` works without the adapter.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={},
            sass_variables=self.sass_variables_v1,
        )
        assert site_configuration._get_theme_v1_variables_overrides()

    def test_theme_v2_variables_overrides_without_adapter_old_variables(self):
        """
        Ensure `_get_theme_v2_variables_overrides()` checks of a v2 type CSS variables.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={},
            sass_variables=self.sass_variables_v1,
        )
        with pytest.raises(Exception, match='expects a theme v2 dictionary of css variables'):
            assert site_configuration._get_theme_v2_variables_overrides()

    def test_theme_v2_variables_overrides_without_adapter_new_variables(self):
        """
        Ensure `_get_theme_v2_variables_overrides()` works with v2 type CSS variables.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={},
            sass_variables=self.sass_variables_v2,
        )
        assert site_configuration._get_theme_v2_variables_overrides()

    def test_theme_v2_variables_overrides_with_adapter(self):
        """
        Ensure `_get_theme_v2_variables_overrides()` works with the adapter.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={},
            sass_variables={},
        )
        site_configuration._api_adapter = self.api_adapter
        assert site_configuration._get_theme_v2_variables_overrides()

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
        site_configuration._api_adapter = self.api_adapter
        assert site_configuration.get_page_content('about') == {
            'title': 'About page from site configuration service',
        }

    def test_secret_without_adapter(self):
        """
        Test `get_secret_value()` without the SiteConfig adapter.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={
                'SEGMENT_KEY': 'dummy-secret-from-model'
            }
        )
        assert site_configuration.get_secret_value('SEGMENT_KEY') == 'dummy-secret-from-model'

    def test_secret_with_adapter(self):
        """
        Ensure `get_secret_value()` uses the SiteConfig adapter when available.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
        )
        site_configuration._api_adapter = self.api_adapter
        assert site_configuration.get_secret_value('SEGMENT_KEY') == 'test-secret-from-service'

    def test_admin_config_without_adapter(self):
        """
        Test `get_admin_setting()` without the SiteConfig adapter.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
            site_values={
                'IDP_TENANT_ID': 'dummy-tenant-in-model'
            }
        )
        assert site_configuration.get_admin_setting('IDP_TENANT_ID') == 'dummy-tenant-in-model'

    def test_admin_config_with_adapter(self):
        """
        Ensure `get_admin_setting()` uses the SiteConfig adapter when available.
        """
        site_configuration = SiteConfigurationFactory.create(
            site=self.site,
        )
        site_configuration._api_adapter = self.api_adapter
        assert site_configuration.get_admin_setting('IDP_TENANT_ID') == 'dummy-tenant-id'


@pytest.mark.django_db
@patch.dict('django.conf.settings.FEATURES', {'TAHOE_SITE_CONFIG_CLIENT_ORGANIZATIONS_SUPPORT': True})
@patch('openedx.core.djangoapps.appsembler.sites.utils.get_active_organizations')
def test_get_all_orgs_filters_by_active(mock_active_orgs):
    """
    Test `get_all_orgs()` while using TAHOE_SITE_CONFIG_CLIENT_ORGANIZATIONS_SUPPORT.
    """
    OrganizationFactory.create(short_name='red')
    OrganizationFactory.create(short_name='blue')
    inactive_org = OrganizationFactory.create(short_name='inactive')

    fake_active_orgs = Organization.objects.exclude(pk=inactive_org.pk)
    mock_active_orgs.return_value = fake_active_orgs

    all_orgs = configuration_helpers.get_all_orgs()
    assert set(all_orgs) == {'red', 'blue'}, 'Should rely on get_active_organizations'


@pytest.mark.django_db
@patch.dict('django.conf.settings.FEATURES', {'TAHOE_SITE_CONFIG_CLIENT_ORGANIZATIONS_SUPPORT': True})
@patch('openedx.core.djangoapps.appsembler.sites.utils.get_active_organizations')
def test_get_configuration_for_org_via_short_name(mock_active_orgs):
    """
    Test `get_configuration_for_org()` while using TAHOE_SITE_CONFIG_CLIENT_ORGANIZATIONS_SUPPORT.

    This method tests get_configuration_for_org indirectly.
    """
    mock_active_orgs.return_value = Organization.objects.all()

    unconfigured_url = configuration_helpers.get_value_for_org('blue1', 'blog_url', default='default_url')
    assert unconfigured_url == 'default_url', 'Should return default value'

    with with_organization_context(site_color='blue1', configs={'blog_url': 'http://blog.com'}):
        # Configure the organization
        configured_blog_url = configuration_helpers.get_value_for_org('blue1', 'blog_url', default='default_url')

    assert configured_blog_url == 'http://blog.com', 'should read from site configs properly'


@pytest.mark.django_db
@patch.dict('django.conf.settings.FEATURES', {'TAHOE_SITE_CONFIG_CLIENT_ORGANIZATIONS_SUPPORT': True})
@patch('openedx.core.djangoapps.appsembler.sites.utils.get_active_organizations')
def test_get_configuration_for_org_via_short_name_inactive_org(mock_active_orgs):
    """
    Test `get_configuration_for_org()` with expired subscription while using

    This method tests get_configuration_for_org with TAHOE_SITE_CONFIG_CLIENT_ORGANIZATIONS_SUPPORT indirectly.
    """
    mock_active_orgs.return_value = Organization.objects.none()
    inactive_org_url = configuration_helpers.get_value_for_org('blue1', 'blog_url', default='default_url')
    assert inactive_org_url == 'default_url', 'If the organization is not active, ignore its configurations'
