import json
import os
import pkg_resources

from django.conf import settings
from django.core.serializers.python import Deserializer
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import (
    connections,
    DatabaseError,
    DEFAULT_DB_ALIAS,
    IntegrityError,
    router,
    transaction,
)


class Command(BaseCommand):
    """
    Imports Tahoe site objects from an export file.
    """
    # Increase this version by 1 after every backward-incompatible
    # change in the exported data format
    VERSION = 1

    def __init__(self, *args, **kwargs):
        self.debug = False
        self.using = DEFAULT_DB_ALIAS
        self.version = self.VERSION
        self.ignore = False

        super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            help='The path of the exports file.',
            type=str,
        )
        parser.add_argument(
            '-d', '--debug',
            action='store_true',
            default=settings.DEBUG,
            help='Execute in debug mode (Will not commit or save changes).'
        )
        parser.add_argument(
            '--database', default=DEFAULT_DB_ALIAS,
            help='Nominates a specific database to load export data into. Defaults to the "default" database.',
        )
        parser.add_argument(
            '--ignorenonexistent', '-i', action='store_true', dest='ignore',
            help='Ignores entries in the serialized data for fields that do not '
                 'currently exist on the model.',
        )

    def handle(self, *args, **options):
        """
        Verifies the input and packs the site objects.
        """
        self.debug = options['debug']
        self.ignore = options['ignore']
        self.using = options['database']

        path = options['path']

        exports = self.process_input(path)
        self.check_project(exports)

        self.stdout.write('\nProcessing %s site objects...' % exports['site_domain'])

        # If loaddata is successfully completed, the changes are committed to
        # the database. If there is an exception, the changes are rolled back.
        with transaction.atomic(using=self.using):
            self.loaddata(exports['objects'])

        # Close the DB connection -- unless we're still in a transaction. This
        # is required as a workaround for an edge case in MySQL: if the same
        # connection is used to create tables, load data, and query, the query
        # can return incorrect results. See Django #7572, MySQL #37735.
        if transaction.get_autocommit(self.using):
            connections[self.using].close()

        self.stdout.write(self.style.SUCCESS('\nSuccessfully imported "%s" site objects.' % exports['site_domain']))

    def process_input(self, path):
        """
        Processes the input path, by fetching the file and returning the JSON
        representation of it.
        """
        self.stdout.write('Fetching exports file content...')
        if not os.path.exists(path):
            raise CommandError('Exports file path does not exist: %s' % path)

        with open(path) as f:
            data = json.load(f)

        return data

    def check_project(self, exports):
        """
        Inspects project for potential problems.
        """
        self.stdout.write('Inspecting project for potential problems...')
        self.check(display_num_errors=True)

        if not exports.get('site_domain'):
            raise CommandError('Malformed exports file.')

        if exports['version'] != self.version:
            self.stdout.write(self.style.WARNING('Version mismatch between exported input and the importer.'))
            self.stdout.write(self.style.HTTP_INFO('Objects will be created as long as no errors happen on the way.'))

        local_packages = self.get_pip_packages()
        exported_packages = exports['libraries']

        if exported_packages != local_packages:
            self.stdout.write(self.style.WARNING('Pip packages mismatch between exported input and the importer.'))
            self.stdout.write(self.style.HTTP_INFO('Objects will be created as long as no errors happen on the way.'))

            if self.debug:
                packages = {
                    key: (local_packages.get(key), exported_packages.get(key))
                    for key in set(local_packages).union(exported_packages)
                }

                for package, (local_version, exported_version) in packages.items():
                    if local_version != exported_version:
                        if not local_version:
                            self.stdout.write('%s==%s not found in your local env' % (package, exported_version))
                        elif not exported_version:
                            self.stdout.write('%s==%s not found in your exported env.' % (package, exported_version))
                        else:
                            self.stdout.write(
                                '%s local version is %s and exported version is %s'
                                % (package, local_version, exported_version)
                            )
            else:
                self.stdout.write('Turn debugging mode on to see packages differences')

    def get_pip_packages(self):
        """
        Returns a dictionary of pip packages names and their versions. Similar
        to `$ pip freeze`
        """
        return {
            package.project_name: package.version
            for package in pkg_resources.working_set
        }

    def loaddata(self, objects_data):
        connection = connections[self.using]

        self.loaded_object_count = 0
        self.export_object_count = 0
        self.models = set()

        with connection.constraint_checks_disabled():
            self.load_objects(objects_data)

        # Since we disabled constraint checks, we must manually check for
        # any invalid keys that might have been added
        table_names = [model._meta.db_table for model in self.models]

        try:
            connection.check_constraints(table_names=table_names)
        except Exception as e:
            e.args = ('Problem loading site: %s' % e,)
            raise

        # If we found even one object in a export, we need to reset the
        # database sequences.
        if self.loaded_object_count > 0:
            sequence_sql = connection.ops.sequence_reset_sql(no_style(), self.models)
            if sequence_sql:
                self.stdout.write('Resetting sequences\n')
                with connection.cursor() as cursor:
                    for line in sequence_sql:
                        cursor.execute(line)

        if self.export_object_count == self.loaded_object_count:
            self.stdout.write('Installed %d object(s)' % self.loaded_object_count)
        else:
            self.stdout.write(
                'Installed %d object(s) (of %d)'
                % (self.loaded_object_count, self.export_object_count)
            )

    def load_objects(self, objects_data):
        """
        Creates the objects one by one.
        """
        self.stdout.write('Processing objects in progress...')

        models = set()
        objects = Deserializer(objects_data, using=self.using, ignorenonexistent=self.ignore)

        try:
            for obj in objects:
                self.export_object_count += 1
                if router.allow_migrate_model(self.using, obj.object.__class__):
                    self.loaded_object_count += 1
                    models.add(obj.object.__class__)
                    try:
                        obj.save(using=self.using)
                        self.stdout.write('\rProcessed %i object(s).' % self.loaded_object_count, ending='')
                    except AttributeError:
                        continue
                    except (DatabaseError, IntegrityError) as e:
                        e.args = ('Could not load %(app_label)s.%(object_name)s(pk=%(pk)s): %(error_msg)s' % {
                            'app_label': obj.object._meta.app_label,
                            'object_name': obj.object._meta.object_name,
                            'pk': obj.object.pk,
                            'error_msg': e,
                        },)
                        raise

            if objects:
                self.stdout.write('')  # Add a newline after progress indicator.
        except Exception as e:
            if not isinstance(e, CommandError):
                e.args = ('Problem loading site %s' % e,)
            raise

        # Warn if the the export file we loaded contains 0 objects.
        if self.export_object_count == 0:
            self.stdout.write(self.style.WARNING('No data found for provided export file'))
