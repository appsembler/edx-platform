"""
Django models for site configurations.
"""

import beeline

import collections
from logging import getLogger
from sass import CompileError

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.files.storage import get_storage_class
from django.db import models
from django.db.models.signals import post_save, pre_save, post_init
from django.dispatch import receiver
from django.utils.encoding import python_2_unicode_compatible
from jsonfield.fields import JSONField
from model_utils.models import TimeStampedModel

from .exceptions import TahoeConfigurationException
from ..appsembler.sites.waffle import ENABLE_CONFIG_VALUES_MODIFIER

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
    tahoe_config_modifier = None  # Tahoe: Placeholder for `TahoeConfigurationValueModifier` instance

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

    @beeline.traced('site_config.get_value')
    def get_value(self, name, default=None):
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
            if self.tahoe_config_modifier:
                name, default = self.tahoe_config_modifier.normalize_get_value_params(name, default)
                should_override, overridden_value = self.tahoe_config_modifier.override_value(name)
                if should_override:
                    return overridden_value

            try:
                if self.api_adapter:
                    # Tahoe: Use `SiteConfigAdapter` if available.
                    beeline.add_context_field('value_source', 'site_config_service')
                    return self.api_adapter.get_value_of_type(self.api_adapter.TYPE_SETTING, name, default)
                else:
                    beeline.add_context_field('value_source', 'django_model')
                    return self.site_values.get(name, default)
            except AttributeError as error:
                logger.exception(u'Invalid JSON data. \n [%s]', error)
        else:
            logger.info(u"Site Configuration is not enabled for site (%s).", self.site)

        return default

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
        """
        Compiles the microsite sass and save it into the storage bucket.

        :return dict {
          "successful_sass_compile": boolean: whether the CSS was compiled successfully
          "sass_compile_message": string: Status message that's safe to show for customers.
        }
        """
        # Importing `sites.utils` locally to avoid test-time Django errors.
        # TODO: Fix Site Configuration and Organizations hacks. https://github.com/appsembler/edx-platform/issues/329
        from openedx.core.djangoapps.appsembler.sites import utils as sites_utils

        storage = self.get_customer_themes_storage()
        css_file_name = self.get_value('css_overrides_file')
        if not css_file_name:
            developer_message = 'Skipped compiling due to missing `css_overrides_file`'
            exception_message = 'Tahoe: {developer_message} for `{site}` config_id=`{config_id}`'.format(
                developer_message=developer_message,
                site=self.site.domain,
                config_id=self.id,
            )
            logger.exception(exception_message, exc_info=TahoeConfigurationException(exception_message))
            return {
                'successful_sass_compile': False,
                'sass_compile_message': developer_message,
            }

        theme_version = self.get_value('THEME_VERSION', 'amc-v1')
        if theme_version == 'tahoe-v2':
            scss_file = '_main-v2.scss'
        else:
            # TODO: Deprecated. Remove once all sites are migrated to Tahoe 2.0 structure.
            scss_file = 'main.scss'

        try:
            css_output = sites_utils.compile_sass(scss_file, custom_branding=self._sass_var_override)
            with storage.open(css_file_name, 'w') as f:
                f.write(css_output)
            successful_sass_compile = True
            sass_compile_message = 'Sass compile finished successfully for site {site}'.format(site=self.site.domain)
        except CompileError as exc:
            successful_sass_compile = False
            sass_compile_message = 'Sass compile failed for site {site} with the error: {message}'.format(
                site=self.site.domain,
                message=str(exc),
            )
            logger.warning(sass_compile_message, exc_info=True)

        return {
            'successful_sass_compile': successful_sass_compile,
            'sass_compile_message': sass_compile_message,
            'scss_file_used': scss_file,
        }

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


@receiver(post_init, sender=SiteConfiguration)
def tahoe_update_site_values_on_save(sender, instance, **kwargs):
    """
    Initialize `api_adapter` property for `SiteConfiguration`.
    """
    if instance and not instance.api_adapter:
        # Tahoe: Import is placed here to avoid model import at project startup
        from openedx.core.djangoapps.appsembler.sites import (
            site_config_client_helpers as site_helpers,
        )
        if site_helpers.is_enabled_for_site(instance.site):
            instance.api_adapter = site_helpers.get_configuration_adapter(instance.site)


@receiver(pre_save, sender=SiteConfiguration)
def tahoe_update_site_values_on_save(sender, instance, **kwargs):
    """
    Temp. helper until ENABLE_CONFIG_VALUES_MODIFIER is enabled on production.

    # TODO: RED-2828 Clean up after production QA
    """
    if not ENABLE_CONFIG_VALUES_MODIFIER.is_enabled():
        logger.info('ENABLE_CONFIG_VALUES_MODIFIER: switch is disabled, saving override values inline.')
        from openedx.core.djangoapps.appsembler.sites.config_values_modifier import TahoeConfigurationValueModifier
        tahoe_config_modifier = TahoeConfigurationValueModifier(site_config_instance=instance)

        if not instance.site_values:
            instance.site_values = {}

        if not instance.site_values.get('platform_name'):
            instance.site_values['platform_name'] = instance.site.name

        if not instance.site_values.get('PLATFORM_NAME'):  # First-time the config is saved with save()
            instance.site_values['css_overrides_file'] = tahoe_config_modifier.get_css_overrides_file()
            instance.site_values['ENABLE_COMBINED_LOGIN_REGISTRATION'] = True

        # Everytime the config is saved with save()
        instance.site_values.update({
            'PLATFORM_NAME': instance.site_values.get('platform_name', ''),
            'LANGUAGE_CODE': instance.site_values.get('LANGUAGE_CODE', 'en'),
            'LMS_ROOT_URL': tahoe_config_modifier.get_lms_root_url(),
            'SITE_NAME': tahoe_config_modifier.get_domain(),
            'ACTIVATION_EMAIL_SUPPORT_LINK': tahoe_config_modifier.get_activation_email_support_link(),
            'PASSWORD_RESET_SUPPORT_LINK': tahoe_config_modifier.get_password_reset_support_link(),
        })


@receiver(post_save, sender=SiteConfiguration)
def compile_tahoe_microsite_sass_on_site_config_save(sender, instance, created, **kwargs):
    """
    Tahoe: Compile Tahoe microsite scss on saving the SiteConfiguration model.

    This signal receiver maintains backward compatibility with existing sites and the Appsembler Management
    Console (AMC).

    # TODO: RED-2847 - Remove this signal receiver after all Tahoe sites switch to Dashboard.
    """
    sass_status = instance.compile_microsite_sass()
    if sass_status['successful_sass_compile']:
        logger.info('tahoe sass compiled successfully: %s', sass_status['sass_compile_message'])
    else:
        logger.warning('tahoe css compile error: %s', sass_status['sass_compile_message'])


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
