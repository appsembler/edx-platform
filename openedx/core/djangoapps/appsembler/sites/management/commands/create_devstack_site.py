import hashlib
import inspect
import json
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.core.validators import validate_slug, ValidationError
from django.conf import settings

from openedx.core.djangoapps.appsembler.sites.serializers import RegistrationSerializer
from openedx.core.djangoapps.appsembler.sites.utils import reset_amc_tokens
from student.models import UserProfile
from student.roles import CourseCreatorRole


class Command(BaseCommand):
    """
    Create the demo something.localhost:18000 site for devstack.

    Needs the corresponding `create_devstack_site` AMC command to be run as well.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            'name',
            help='A slug for the username and used as a site name prefix e.g. something.localhost:18000',
            nargs=1,
            type=str,
        )

    def congrats(self, **kwargs):
        """
        Write a congrats message.

        :param kwargs: congrats message format keyword arguments.
        """
        self.stdout.write(inspect.cleandoc(
            """
            Congrats, Your site is ready!

            Username: "{name}"
            Email: "{email}"
            Password: "{password}"

            Site URL: "http://{site}/"

            Please add the following entry to your /etc/hosts file:

                127.0.0.1 {domain}

            Remember to run the corresponding AMC command.

            Enjoy!
            """.format(**kwargs)
        ))

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('This only works on devstack.')

        name = options['name'][0].lower()
        try:
            validate_slug(name)
        except ValidationError:
            raise CommandError('Please enter a valid slug')

        if User.objects.filter(username=name).exists():
            raise CommandError('User exists with the username: "{}". Please choose another name.'.format(name))

        domain = '{}.localhost'.format(name)
        site_name = '{}:18000'.format(domain)

        user = User.objects.create_user(
            username=name,
            email='{}@example.com'.format(name),
            password=name,
        )
        CourseCreatorRole().add_users(user)
        UserProfile.objects.create(user=user, name=name)

        # Calculated access tokens to the AMC devstack can have them without needing to communicate with the LMS.
        # Just making it easier to automate this without having cross-dependency in devstack
        fake_token = hashlib.md5(user.username).hexdigest()
        reset_amc_tokens(user, access_token=fake_token, refresh_token=fake_token)

        data = {
            'site': {
                'domain': site_name,
                'name': site_name,
            },
            'user_email': user.email,
            'organization': {
                'name': name,
                'short_name': name,
                'edx_uuid': uuid.uuid4(),
            },
            'initial_values': {
                'SITE_NAME': site_name,
                'platform_name': '{} Academy'.format(name),
                'logo_positive': None,
                'logo_negative': None,
                'font': 'Roboto',
                'accent-font': 'Delius Unicase',
                'primary_brand_color': '#F00',
                'base_text_color': '#000',
                'cta_button_bg': '#00F',
            }
        }
        serializer = RegistrationSerializer(data=data)
        if not serializer.is_valid():
            raise CommandError('Something went wrong with the process: \n{errors}'.format(
                errors=json.dumps(serializer.errors, indent=4)
            ))
        serializer.save()

        self.congrats(
            name=user.username,
            email=user.email,
            password=name,
            site=site_name,
            domain=domain,
        )
