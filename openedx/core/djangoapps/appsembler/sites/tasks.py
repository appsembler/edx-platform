from celery.task import task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.db import transaction

from organizations.models import UserOrganizationMapping, Organization
from openedx.core.djangoapps.theming.models import SiteTheme
from organizations.api import add_organization


log = get_task_logger(__name__)


@task(bind=True, default_retry_delay=300, max_retries=5)
def bootstrap_site(self, site, organization_id=None, user_email=None):
    from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
    # don't use create because we need to call save() to set some values automatically
    try:
        with transaction.atomic():
            site_config = SiteConfiguration(site=site, enabled=True)
            site_config.save()
            SiteTheme.objects.create(site=site, theme_dir_name=settings.THEME_NAME)
            site.configuration_id = site_config.id
            # temp workarounds while old staging is still up and running
            ret = {}
            ret['site_id'] = site.id
            if organization_id:
                organization_data = add_organization({
                    'name': organization_id,
                    'short_name': organization_id
                })
                organization = Organization.objects.get(id=organization_data.get('id'))
                site_config.values['course_org_filter'] = organization_id
                site_config.save()
                ret['organization_id'] = organization.id
            else:
                ret['organization_id'] = None

            if user_email:
                user = User.objects.get(email=user_email)
                UserOrganizationMapping.objects.create(user=user, organization=organization)
                ret['user_id'] = user.id
            else:
                ret['user_id'] = None
            return ret
    except Exception as e:
        log.error('Failed to bootstrap site: {0}'.format(str(e)))
        self.retry(e)


@task(bind=True, default_retry_delay=300, max_retries=5)
def delete_site(self, site_id):
    try:
        with transaction.atomic():
            site = Site.objects.get(id=site_id)
            site.configuration.delete()
            site.themes.delete()
            site.delete()
    except Exception as e:
        log.error("Failed to delete site: {0}".format(str(e)))
        self.retry(e)

