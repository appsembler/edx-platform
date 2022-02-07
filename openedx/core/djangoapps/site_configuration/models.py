"""
Django models for site configurations.
"""


import beeline

import collections
from logging import getLogger
import os
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.files.storage import get_storage_class
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.encoding import python_2_unicode_compatible
from jsonfield.fields import JSONField
from model_utils.models import TimeStampedModel

from .exceptions import TahoeConfigurationException

logger = getLogger(__name__)  # pylint: disable=invalid-name


def get_initial_sass_variables():
    """
    Proxy to `utils.get_initial_sass_variables` to avoid test-time Django errors.

    # TODO: Fix Site Configuration and Organizations hacks. https://github.com/appsembler/edx-platform/issues/329
    """
    from openedx.core.djangoapps.appsembler.sites import utils
    return utils.get_initial_sass_variables()


def get_initial_page_elements():
    """
    Proxy to `utils.get_initial_page_elements` to avoid test-time Django errors.

    # TODO: Fix Site Configuration and Organizations hacks. https://github.com/appsembler/edx-platform/issues/329
    """
    from openedx.core.djangoapps.appsembler.sites import utils
    return utils.get_initial_page_elements()


@python_2_unicode_compatible
class SiteConfiguration(models.Model):
    """
    Model for storing site configuration. These configuration override OpenEdx configurations and settings.
    e.g. You can override site name, logo image, favicon etc. using site configuration.

    Fields:
        site (OneToOneField): one to one field relating each configuration to a single site
        site_values (JSONField):  json field to store configurations for a site

    .. no_pii:
    """

    api_adapter = None  # Tahoe: Placeholder for `site_config_client`'s `SiteConfigAdapter`
    cached_hardcoded_values = None  # Tahoe: Used by `get_tahoe_hardcoded_values`

    site = models.OneToOneField(Site, related_name='configuration', on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False, verbose_name=u"Enabled")
    site_values = JSONField(
        null=False,
        blank=True,
        # The actual default value is determined by calling the given callable.
        # Therefore, the default here is just {}, since that is the result of
        # calling `dict`.
        default=dict,
        load_kwargs={'object_pairs_hook': collections.OrderedDict}
    )
    sass_variables = JSONField(blank=True, default=get_initial_sass_variables)
    page_elements = JSONField(blank=True, default=get_initial_page_elements)

    def __str__(self):
        return u"<SiteConfiguration: {site} >".format(site=self.site)  # xss-lint: disable=python-wrap-html

    def __repr__(self):
        return self.__str__()

    def save(self, **kwargs):
        super().save(**kwargs)
        # recompile SASS on every save
        self.compile_microsite_sass()  # TODO: Implement via signals, instead of overriding the "save" method.
        return self

    @beeline.traced('site_config.init_api_client_adapter')
    def init_api_client_adapter(self, site):
        """
        Initialize `api_adapter`, this method is managed externally by `get_current_site_configuration()`.
        """
        # Tahoe: Import is placed here to avoid model import at project startup
        from openedx.core.djangoapps.appsembler.sites import (
            site_config_client_helpers as site_helpers,
        )
        if site_helpers.is_enabled_for_site(site):
            self.api_adapter = site_helpers.get_configuration_adapter(site)

    @beeline.traced('site_config.get_tahoe_hardcoded_values')
    def get_tahoe_hardcoded_values(self):
        """
        Tahoe: Getting saner defaults for Tahoe.

        Given a value, return a hard-coded default completely disregarding the stored values.
        These default site values are derived from site values.
        """
        if not self.cached_hardcoded_values:
            site_domain = self.site.domain
            domain_without_port_number = site_domain.split(':')[0]

            # We cannot simply use a protocol-relative URL for LMS_ROOT_URL
            # This is because the URL here will be used by such activities as
            # sending activation links to new users. The activation link needs the
            # scheme address verification emails. The callers using this variable
            # expect the scheme in the URL
            root_url = '{scheme}://{domain}'.format(
                scheme=urlsplit(settings.LMS_ROOT_URL).scheme,
                domain=site_domain,
            )

            self.cached_hardcoded_values = {
                'PLATFORM_NAME': self._get_value('platform_name'),
                'css_overrides_file': "{}.css".format(domain_without_port_number),
                'ENABLE_COMBINED_LOGIN_REGISTRATION': True,
                'LMS_ROOT_URL': root_url,
                'SITE_NAME': site_domain,  # Support for custom domains.
                # RED-2471: Use Multi-tenant `/help` URL for password reset emails.
                'ACTIVATION_EMAIL_SUPPORT_LINK': '{root_url}/help'.format(root_url=root_url),
                # RED-2385: Use Multi-tenant `/help` URL for activation emails.
                'PASSWORD_RESET_SUPPORT_LINK': '{root_url}/help'.format(root_url=root_url),
            }

        return self.cached_hardcoded_values

    @beeline.traced('site_config.get_value')
    def get_value(self, name, default=None):
        """
        Tahoe: Return configuration value with hardcoded Tahoe values.
        """
        if name == 'LANGUAGE_CODE' and default is None:
            # TODO: Ask Dashboard 2.0 / AMC to set the `LANGUAGE_CODE` by default.
            default = 'en'

        hardcoded_values = self.get_tahoe_hardcoded_values()
        if name in hardcoded_values:
            # Disregard the stored value, and return a Tahoe-compatible version.
            return hardcoded_values[name]
        else:
            return self._get_value(name, default)

    @beeline.traced('site_config._get_value')
    def _get_value(self, name, default=None):
        """
        Return Configuration value for the key specified as name argument.

        Function logs a message if configuration is not enabled or if there is an error retrieving a key.

        Args:
            name (str): Name of the key for which to return configuration value.
            default: default value tp return if key is not found in the configuration

        Returns:
            Configuration value for the given key or returns `None` if configuration is not enabled.
        """
        beeline.add_context_field('value_name', name)
        if self.enabled:
            try:
                if self.api_adapter:
                    # Tahoe: Use `SiteConfigAdapter` if available.
                    beeline.add_context_field('value_source', 'site_config_service')
                    return self.api_adapter.get_value(name, default)
                else:
                    beeline.add_context_field('value_source', 'django_model')
                    return self.site_values.get(name, default)
            except AttributeError as error:
                logger.exception(u'Invalid JSON data. \n [%s]', error)
        else:
            logger.info(u"Site Configuration is not enabled for site (%s).", self.site)

        return default

    @beeline.traced('site_config.get_page_content')
    def get_page_content(self, name, default=None):
        """
        Tahoe: Get page content from Site Configuration service settings.

        If SiteConfiguration adapter isn't in use, fallback to the deprecated `SiteConfiguration.page_elements` field.

        Args:
            name (str): Name of the page to fetch.
            default: default value to return if page is not found in the configuration.

        Returns:
            Page content `dict`.
        """
        if self.api_adapter:
            beeline.add_context_field('page_source', 'site_config_service')
            return self.api_adapter.get_amc_v1_page(name, default)
        else:
            beeline.add_context_field('page_source', 'django_model')
            return self.page_elements.get(name, default)

    @classmethod
    def get_configuration_for_org(cls, org, select_related=None):
        """
        This returns a SiteConfiguration object which has an org_filter that matches
        the supplied org

        Args:
            org (str): Org to use to filter SiteConfigurations
            select_related (list or None): A list of values to pass as arguments to select_related
        """
        query = cls.objects.filter(site_values__contains=org, enabled=True)

        if hasattr(SiteConfiguration, 'sass_variables'):
            # TODO: Clean up Site Configuration hacks: https://github.com/appsembler/edx-platform/issues/329
            query = query.defer('page_elements', 'sass_variables')

        if select_related is not None:
            query = query.select_related(*select_related)
        for configuration in query:
            course_org_filter = configuration.get_value('course_org_filter', [])
            # The value of 'course_org_filter' can be configured as a string representing
            # a single organization or a list of strings representing multiple organizations.
            if not isinstance(course_org_filter, list):
                course_org_filter = [course_org_filter]
            if org in course_org_filter:
                return configuration
        return None

    @classmethod
    def get_value_for_org(cls, org, name, default=None):
        """
        This returns site configuration value which has an org_filter that matches
        what is passed in,

        Args:
            org (str): Course ord filter, this value will be used to filter out the correct site configuration.
            name (str): Name of the key for which to return configuration value.
            default: default value tp return if key is not found in the configuration

        Returns:
            Configuration value for the given key.
        """
        configuration = cls.get_configuration_for_org(org)
        if configuration is None:
            return default
        else:
            return configuration.get_value(name, default)

    @classmethod
    def get_all_orgs(cls):
        """
        This returns all of the orgs that are considered in site configurations, This can be used,
        for example, to do filtering.

        Returns:
            A set of all organizations present in site configuration.
        """
        org_filter_set = set()

        query = cls.objects.filter(site_values__contains='course_org_filter', enabled=True)
        if hasattr(SiteConfiguration, 'sass_variables'):
            # TODO: Clean up Site Configuration hacks: https://github.com/appsembler/edx-platform/issues/329
            query = query.defer('page_elements', 'sass_variables')

        for configuration in query:
            course_org_filter = configuration.get_value('course_org_filter', [])
            if not isinstance(course_org_filter, list):
                course_org_filter = [course_org_filter]
            org_filter_set.update(course_org_filter)
        return org_filter_set

    @classmethod
    def has_org(cls, org):
        """
        Check if the given organization is present in any of the site configuration.

        Returns:
            True if given organization is present in site configurations otherwise False.
        """
        return org in cls.get_all_orgs()

    def delete(self, using=None):
        self.delete_css_override()
        super(SiteConfiguration, self).delete(using=using)

    def compile_microsite_sass(self):
        # Importing `compile_sass` to avoid test-time Django errors.
        # TODO: Fix Site Configuration and Organizations hacks. https://github.com/appsembler/edx-platform/issues/329
        from openedx.core.djangoapps.appsembler.sites.utils import compile_sass
        css_output = compile_sass('main.scss', custom_branding=self._sass_var_override)
        file_name = self.get_value('css_overrides_file')

        if not file_name:
            if settings.TAHOE_SILENT_MISSING_CSS_CONFIG:
                return  # Silent the exception below on during testing
            else:
                raise TahoeConfigurationException(
                    'Missing `css_overrides_file` from SiteConfiguration for `{site}` config_id=`{id}`'.format(
                        site=self.site.domain,
                        id=self.id,
                    )
                )

        storage = self.get_customer_themes_storage()
        with storage.open(file_name, 'w') as f:
            f.write(css_output)

    def get_css_url(self):
        storage = self.get_customer_themes_storage()
        return storage.url(self.get_value('css_overrides_file'))

    def set_sass_variables(self, entries):
        """
        Accepts a dict with the shape { var_name: value } and sets the SASS variables
        """
        for index, entry in enumerate(self.sass_variables):
            var_name = entry[0]
            if var_name in entries:
                new_value = (var_name, [entries[var_name], entries[var_name]])
                self.sass_variables[index] = new_value

    def get_customer_themes_storage(self):
        storage_class = get_storage_class(settings.DEFAULT_FILE_STORAGE)
        return storage_class(**settings.CUSTOMER_THEMES_BACKEND_OPTIONS)

    def delete_css_override(self):
        css_file = self.get_value('css_overrides_file')
        if css_file:
            try:
                storage = self.get_customer_themes_storage()
                storage.delete(self.get_value('css_overrides_file'))
            except Exception:  # pylint: disable=broad-except  # noqa
                logger.warning("Can't delete CSS file {}".format(css_file))

    @beeline.traced('site_config._formatted_sass_variables')
    def _formatted_sass_variables(self):
        if self.api_adapter:
            # Tahoe: Use `SiteConfigAdapter` if available.
            beeline.add_context_field('value_source', 'site_config_service')
            sass_variables = self.api_adapter.get_amc_v1_theme_css_variables()
        else:
            beeline.add_context_field('value_source', 'django_model')
            sass_variables = self.sass_variables
        return " ".join(["{}: {};".format(var, val[0]) for var, val in sass_variables])

    def _sass_var_override(self, path):
        if 'branding-basics' in path:
            return [(path, self._formatted_sass_variables())]
        if 'customer-sass-input' in path:
            return [(path, self.get_value('customer_sass_input', ''))]
        return None


def save_siteconfig_without_historical_record(siteconfig, *args, **kwargs):
    """
    Save model without saving a historical record

    Make sure you know what you're doing before you use this method.

    Note: this method is copied verbatim from django-simple-history.
    """
    siteconfig.skip_history_when_saving = True
    try:
        ret = siteconfig.save(*args, **kwargs)
    finally:
        del siteconfig.skip_history_when_saving
    return ret


@python_2_unicode_compatible
class SiteConfigurationHistory(TimeStampedModel):
    """
    This is an archive table for SiteConfiguration, so that we can maintain a history of
    changes. Note that the site field is not unique in this model, compared to SiteConfiguration.

    Fields:
        site (ForeignKey): foreign-key to django Site
        site_values (JSONField): json field to store configurations for a site

    .. no_pii:
    """
    site = models.ForeignKey(Site, related_name='configuration_histories', on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False, verbose_name=u"Enabled")
    site_values = JSONField(
        null=False,
        blank=True,
        load_kwargs={'object_pairs_hook': collections.OrderedDict}
    )

    class Meta:
        get_latest_by = 'modified'
        ordering = ('-modified', '-created',)

    def __str__(self):
        # pylint: disable=line-too-long
        return u"<SiteConfigurationHistory: {site}, Last Modified: {modified} >".format(  # xss-lint: disable=python-wrap-html
            modified=self.modified,
            site=self.site,
        )

    def __repr__(self):
        return self.__str__()


@receiver(post_save, sender=SiteConfiguration)
def update_site_configuration_history(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    """
    Add site configuration changes to site configuration history.

    Recording history on updates and deletes can be skipped by first setting
    the `skip_history_when_saving` attribute on the instace, e.g.:

      site_config.skip_history_when_saving = True
      site_config.save()

    Args:
        sender: sender of the signal i.e. SiteConfiguration model
        instance: SiteConfiguration instance associated with the current signal
        created (bool): True if a new record was created.
        **kwargs: extra key word arguments
    """
    # Skip writing history when asked by the caller.  This skip feature only
    # works for non-creates.
    if created or not hasattr(instance, "skip_history_when_saving"):
        SiteConfigurationHistory.objects.create(
            site=instance.site,
            site_values=instance.site_values,
            enabled=instance.enabled,
        )
