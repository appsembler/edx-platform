"""
Tests for the create_or_update_site_configuration management command.
"""
from __future__ import absolute_import, unicode_literals

import unittest
from django.conf import settings

import codecs
import json

import ddt
from django.contrib.sites.models import Site
from django.core.management import call_command, CommandError
from django.test import TestCase
from path import Path

from openedx.core.djangoapps.site_configuration.models import SiteConfiguration


@ddt.ddt
@unittest.skipIf(
    settings.TAHOE_ALWAYS_SKIP_TEST,
    'skip low-priority broken upstream tests due to Tahoe changes on the SiteConfiguration model',
)
class CreateOrUpdateSiteConfigurationTest(TestCase):
    """
    Test for the create_or_update_site_configuration management command.
    """
    command = 'create_or_update_site_configuration'

    def setUp(self):
        super(CreateOrUpdateSiteConfigurationTest, self).setUp()
        self.site_id = 1
        self.site_id_arg = ['--site-id', str(self.site_id)]
        self.json_file_path = Path(__file__).parent / "fixtures/config1.json"
        self.input_configuration = {
            'FEATURE_FLAG': True,
            'SERVICE_URL': 'https://foo.bar',
            'ABC': 123,
        }

    @property
    def site(self):
        """
        Return the fixture site for this test class.
        """
        return Site.objects.get(id=self.site_id)

    def assert_site_configuration_does_not_exist(self):
        """
        Assert that the site configuration for the fixture site does not exist.
        """
        with self.assertRaises(SiteConfiguration.DoesNotExist):
            SiteConfiguration.objects.get(site=self.site)

    def get_site_configuration(self):
        """
        Return the site configuration for the fixture site.
        """
        return SiteConfiguration.objects.get(site=self.site)

    def create_fixture_site_configuration(self, enabled):
        SiteConfiguration.objects.update_or_create(
            site=self.site,
            defaults={'enabled': enabled, 'site_values': {'ABC': 'abc', 'B': 'b'}}
        )

    def test_command_no_args(self):
        """
        Verify the error on the command with no arguments.
        """
        with self.assertRaises(CommandError) as error:
            call_command(self.command)
        self.assertIn('Error: one of the arguments --site-id domain is required', str(error.exception))

    def test_site_created_when_site_id_non_existent(self):
        """
        Verify that a new site is created  when given a site ID that doesn't exist.
        """
        non_existent_site_id = 999
        with self.assertRaises(Site.DoesNotExist):
            Site.objects.get(id=non_existent_site_id)

        call_command(self.command, '--site-id', non_existent_site_id)
        Site.objects.get(id=non_existent_site_id)

    def test_site_created_when_domain_non_existent(self):
        """
        Verify that a new site is created when given a domain name that does not have an existing site..
        """
        domain = 'nonexistent.com'
        with self.assertRaises(Site.DoesNotExist):
            Site.objects.get(domain=domain)
        call_command(self.command, domain)
        Site.objects.get(domain=domain)

    def test_both_site_id_domain_given(self):
        """
        Verify that an error is thrown when both site_id and the domain name are provided.
        """
        with self.assertRaises(CommandError) as error:
            call_command(self.command, 'domain.com', '--site-id', '1')

        self.assertIn('not allowed with argument', str(error.exception))

    def test_site_configuration_created_when_non_existent(self):
        """
        Verify that a SiteConfiguration instance is created if it doesn't exist.
        """
        self.assert_site_configuration_does_not_exist()

        call_command(self.command, *self.site_id_arg)
        site_configuration = SiteConfiguration.objects.get(site=self.site)
        self.assertFalse(site_configuration.site_values)
        self.assertFalse(site_configuration.enabled)

    def test_both_enabled_disabled_flags(self):
        """
        Verify the error on providing both the --enabled and --disabled flags.
        """
        with self.assertRaises(CommandError) as error:
            call_command(self.command, '--enabled', '--disabled', *self.site_id_arg)
        self.assertIn('argument --disabled: not allowed with argument --enabled', str(error.exception))

    @ddt.data(('enabled', True),
              ('disabled', False))
    @ddt.unpack
    def test_site_configuration_enabled_disabled(self, flag, enabled):
        """
        Verify that the SiteConfiguration instance is enabled/disabled as per the flag used.
        """
        self.assert_site_configuration_does_not_exist()
        call_command(self.command, '--{}'.format(flag), *self.site_id_arg)
        site_configuration = SiteConfiguration.objects.get(site=self.site)
        self.assertFalse(site_configuration.site_values)
        self.assertEqual(enabled, site_configuration.enabled)

    def test_site_configuration_created_with_parameters(self):
        """
        Verify that a SiteConfiguration instance is created with the provided values if it does not exist.
        """
        self.assert_site_configuration_does_not_exist()
        call_command(self.command, '--configuration', json.dumps(self.input_configuration), *self.site_id_arg)
        site_configuration = self.get_site_configuration()
        self.assertDictEqual(site_configuration.site_values, self.input_configuration)

    def test_site_configuration_created_with_json_file_parameters(self):
        """
        Verify that a SiteConfiguration instance is created with the provided values if it does not exist.
        """
        self.assert_site_configuration_does_not_exist()
        call_command(self.command, '-f', str(self.json_file_path.abspath()), *self.site_id_arg)
        site_configuration = self.get_site_configuration()
        self.assertEqual(site_configuration.site_values, {'ABC': 123, 'XYZ': '789'})

    @ddt.data(True, False)
    def test_site_configuration_updated_with_parameters(self, enabled):
        """
        Verify that the existing parameters are updated when provided in the command.
        """
        self.create_fixture_site_configuration(enabled)
        call_command(self.command, '--configuration', json.dumps(self.input_configuration), *self.site_id_arg)
        site_configuration = self.get_site_configuration()
        self.assertEqual(
            site_configuration.site_values,
            {'ABC': 123, 'B': 'b', 'FEATURE_FLAG': True, 'SERVICE_URL': 'https://foo.bar'}
        )
        self.assertEqual(site_configuration.enabled, enabled)

    @ddt.data(True, False)
    def test_site_configuration_updated_from_json_file(self, enabled):
        """
        Verify that the existing parameteres are updated when provided through a YAML file.
        """
        self.create_fixture_site_configuration(enabled)
        call_command(self.command, '-f', str(self.json_file_path.abspath()), *self.site_id_arg)
        site_configuration = self.get_site_configuration()
        expected_site_configuration = {'ABC': 'abc', 'B': 'b'}
        with codecs.open(self.json_file_path, encoding='utf-8') as f:
            expected_site_configuration.update(json.load(f))
        self.assertEqual(site_configuration.site_values, expected_site_configuration)
        self.assertEqual(site_configuration.enabled, enabled)
