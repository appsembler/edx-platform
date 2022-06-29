"""
Command to remove courses without associated organization.

This command is intended as a follow-up step after `remove_site` but can be run independently.
"""

from django.core.management.base import BaseCommand

from contentstore.utils import delete_course
from xmodule.contentstore.django import contentstore
from xmodule.modulestore import ModuleStoreEnum

from openedx.core.djangoapps.appsembler.sites.utils import get_deletable_course_keys


def delete_course_and_assets(course_key):
    """
    Delete all courses without active organization.
    """
    delete_course(course_key, ModuleStoreEnum.UserID.mgmt_command, keep_instructors=False)
    contentstore().delete_all_course_assets(course_key)


class Command(BaseCommand):
    help = "Delete courses that is not in `get_active_organizations()`."

    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            dest='commit',
            action='store_true',
            default=False,
            help='Remove courses, otherwise only the log will be printed.',
        )

    def handle(self, *args, **options):
        commit = options['commit']

        for course_key in get_deletable_course_keys():
            if commit:
                self.stdout.write('Deleting course: {}'.format(course_key))
                delete_course_and_assets(course_key)
            else:
                self.stdout.write('[Dry run] deleting course: {}'.format(course_key))

        self.stdout.write('Finished removing deletable courses')
