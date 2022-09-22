import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.contrib.sites.models import Site

import lms.lib.comment_client as cc
from organizations.models import Organization
from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
from common.djangoapps.student.roles import CourseAccessRole


log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deletes all user, organization and microsite data." \
           " Keeps the superusers and the default site"

    def handle(self, *args, **options):
        """
        Delete course creator permissions.
        """
        if settings.ROOT_URLCONF == 'lms.urls':
            # TODO: Not important, but cool: Fix the weird dependency and make it work in LMS.
            raise CommandError('Run this command only from CMS, it cannot be run from within LMS.')

        from course_creators.models import CourseCreator  # Keep this import local to avoid errors.
        CourseCreator.objects.all().delete()
        CourseAccessRole.objects.all().delete()

        # remove organizations and users
        for org in Organization.objects.all():
            org.users.exclude(is_superuser=True).delete()
            org.delete()

        # remove sites and site configurations
        for site in Site.objects.exclude(id=settings.SITE_ID):
            try:
                site.configuration.delete()
            except SiteConfiguration.DoesNotExist:
                pass
            site.delete()

        # remove any leftover users that weren't a part of a organization
        users_to_remove = User.objects.exclude(is_superuser=True)
        for user in users_to_remove:
            try:
                comments_user = cc.User.from_django_user(user)
                comments_user.delete()
            except Exception as e:
                log.error("Failed to delete cs_comments_service user {0}. Error {1}".format(
                    user,
                    str(e)))
            user.delete()
