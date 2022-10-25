from django.core.management.base import BaseCommand

from ...deletion_utils import remove_stray_courses_from_mysql


class Command(BaseCommand):
    """
    Bulk removal of courses without an organization linked (aka stray courses).

    This only works for MySQL database.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            help='Maximum number of courses to delete',
            default=1,
            type=int,
        )

        parser.add_argument(
            '--commit',
            help='Otherwise, the transaction would be rolled back.',
            default=False,
            action='store_true',
            dest='commit',
        )

    def handle(self, *args, **options):
        remove_stray_courses_from_mysql(limit=options['limit'], commit=options['commit'])
