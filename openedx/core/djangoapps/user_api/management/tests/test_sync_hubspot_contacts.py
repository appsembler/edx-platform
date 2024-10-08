"""
Test the sync_hubspot_contacts management command
"""


import json
from datetime import timedelta
import unittest

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django.utils.six import StringIO
from mock import patch
from six.moves import range

from openedx.core.djangoapps.site_configuration.tests.factories import SiteConfigurationFactory
from openedx.core.djangoapps.user_api.management.commands.sync_hubspot_contacts import Command as sync_command
from openedx.core.djangolib.testing.utils import skip_unless_lms
from student.models import UserAttribute, UserProfile
from student.tests.factories import UserFactory


@skip_unless_lms
@unittest.skip('Appsembler: Skipping (wontfix) failing upstream tests in Juniper')
class TestHubspotSyncCommand(TestCase):
    """
    Test sync_hubspot_contacts management command.
    """

    @classmethod
    def setUpClass(cls):
        super(TestHubspotSyncCommand, cls).setUpClass()
        cls.site_config = SiteConfigurationFactory()
        cls.hubspot_site_config = SiteConfigurationFactory.create(
            site_values={'HUBSPOT_API_KEY': 'test_key'}
        )
        cls.users = []
        cls._create_users(cls.hubspot_site_config)  # users for a site with hubspot integration enabled
        cls._create_users(cls.site_config)

    @classmethod
    def _create_users(cls, site_conf):
        # Create some test users
        for i in range(1, 20):
            profile_meta = {
                "first_name": "First Name{0}".format(i),
                "last_name": "Last Name{0}".format(i),
                "company": "Company{0}".format(i),
                "title": "Title{0}".format(i),
                "state": "State{0}".format(i),
                "country": "US",
            }
            loe = UserProfile.LEVEL_OF_EDUCATION_CHOICES[0][0]
            date_joined = timezone.now() - timedelta(i)
            user = UserFactory(date_joined=date_joined)
            user_profile = user.profile
            user_profile.level_of_education = loe
            user_profile.meta = json.dumps(profile_meta)
            user_profile.save()  # pylint: disable=no-member
            UserAttribute.set_user_attribute(user, 'created_on_site', site_conf.site.domain)
            cls.users.append(user)

    def test_without_any_hubspot_api_key(self):
        """
        Test no _sync_site call is made if hubspot integration is not enabled for any site
        """
        orig_values = self.hubspot_site_config.site_values
        self.hubspot_site_config.site_values = {}
        self.hubspot_site_config.save()
        sync_site = patch.object(sync_command, '_sync_site')
        mock_sync_site = sync_site.start()
        call_command('sync_hubspot_contacts')
        self.assertFalse(mock_sync_site.called, "_sync_site should not be called")
        sync_site.stop()
        # put values back
        self.hubspot_site_config.site_values = orig_values
        self.hubspot_site_config.save()

    def test_with_initial_sync_days(self):
        """
        Test with providing initial sync days
        """
        sync_with_hubspot = patch.object(sync_command, '_sync_with_hubspot')
        mock_sync_with_hubspot = sync_with_hubspot.start()
        out = StringIO()
        call_command('sync_hubspot_contacts', '--initial-sync-days=7', '--batch-size=2', stdout=out)
        output = out.getvalue()
        self.assertIn('Successfully synced users', output)
        self.assertEqual(mock_sync_with_hubspot.call_count, 4)  # 4 requests of batch (2, 2, 2, 1), total 7 contacts
        sync_with_hubspot.stop()

    def test_command_without_initial_sync_days(self):
        """
        Test sync last day
        """
        sync_with_hubspot = patch.object(sync_command, '_sync_with_hubspot')
        mock_sync_with_hubspot = sync_with_hubspot.start()
        out = StringIO()
        call_command('sync_hubspot_contacts', '--batch-size=3', stdout=out)
        output = out.getvalue()
        self.assertIn('Successfully synced users', output)
        self.assertEqual(mock_sync_with_hubspot.call_count, 1)
        sync_with_hubspot.stop()
