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

        from .config_values_modifier import init_configuration_modifier_for_site_config

        pre_save.connect(patched_clear_site_cache, sender=SiteConfiguration)
        post_init.connect(init_configuration_modifier_for_site_config, sender=SiteConfiguration)
        # Update ALLOWED_HOSTS based on Site model
        site_domains = [site.domain for site in Site.objects.all()]
        settings.ALLOWED_HOSTS.extend(site_domains)
