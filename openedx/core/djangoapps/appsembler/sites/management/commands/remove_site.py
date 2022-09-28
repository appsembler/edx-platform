from django.core.management.base import BaseCommand, CommandError
from django.contrib.sites.models import Site
from django.db import transaction

from openedx.core.djangoapps.appsembler.sites.remove_site_utils import remove_open_edx_site


class Command(BaseCommand):
    """
    Remove a Tahoe website from LMS records.

    Must be used `remove_site` on AMC to avoid any errors there.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            'domain',
            help='The domain of the organization to be deleted.',
            type=str,
        )
        parser.add_argument(
            '--commit',
            default=False,
            dest='commit',
            help='Fully delete the site, otherwise the transaction will be rolled back.',
            action='store_true',
        )

    def handle(self, *args, **options):
        self.stdout.write('Removing "%s" in progress...' % options['domain'])
        remove_open_edx_site(domain=options['domain'], commit=options['commit'])
