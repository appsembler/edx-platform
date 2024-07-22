from django.apps import AppConfig

from django.db.models.signals import pre_save, post_init


class SitesConfig(AppConfig):
    name = 'openedx.core.djangoapps.appsembler.sites'
    label = 'appsembler_sites'

    def ready(self):
        from openedx.core.djangoapps.appsembler.sites.models import patched_clear_site_cache
        from openedx.core.djangoapps.site_configuration.models import SiteConfiguration
        from django.contrib.sites.models import Site
        from django.conf import settings
        from django.core.exceptions import ObjectDoesNotExist

        from .config_values_modifier import init_configuration_modifier_for_site_config

        pre_save.connect(patched_clear_site_cache, sender=SiteConfiguration)
        post_init.connect(init_configuration_modifier_for_site_config, sender=SiteConfiguration)
        # Update ALLOWED_HOSTS based on Site model
        site_domains = []
        sites = Site.objects.all()
        for site in sites:
            site_domains.append(site.domain)
            try:
                alt_domain = site.alternative_domain
                site_domains.append(alt_domain)
            except ObjectDoesNotExist:
                continue
        settings.ALLOWED_HOSTS.extend(site_domains)
