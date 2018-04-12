"""
Management commands for external_courses
"""
import logging

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from openedx.core.djangoapps.appsembler.external_courses.tasks import fetch_courses


class Command(BaseCommand):
    """
    manage.py commands to fetch courses
    """
    help = "fetch courses from external LMS"

    def add_arguments(self, parser):
        parser.add_argument('--pull', action='store_true',
                            help="Pull updated courses.")

    def handle(self, *args, **options):

        if options['pull']:
            log_handler = logging.StreamHandler(self.stdout)
            log_handler.setLevel(logging.DEBUG)
            log = logging.getLogger('external_courses.tasks')
            log.propagate = False
            log.addHandler(log_handler)

            num_added, num_changed, num_failed, num_deleted, num_total = fetch_courses()
            self.stdout.write(
                "\nDone. Fetched {num_total} total. {num_added} where added, {num_changed} were updated, {num_deleted} were deleted and {num_failed} failed.\n".format(
                    num_added=num_added, num_changed=num_changed,
                    num_failed=num_failed, num_total=num_total,
                    num_deleted=num_deleted
                )
            )
        else:
            raise CommandError("Unknown argment: {}".format(subcommand))
