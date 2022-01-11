"""
Site-aware sass compiler and storage manager for the edx-theme-customers Tahoe theme.
"""
from logging import getLogger

import beeline

from django.conf import settings
from django.core.files.storage import get_storage_class

from .helpers import compile_sass

from .exceptions import TahoeConfigurationException

logger = getLogger(__name__)


class ThemeSassManager:
    def __init__(self, site_config, site):
        self.site_config = site_config
        self.site = site

    def compile_microsite_sass(self):
        css_output = compile_sass('main.scss', custom_branding=self._sass_var_override)
        file_name = self.site_config.get_value('css_overrides_file')

        if not file_name:
            if settings.TAHOE_SILENT_MISSING_CSS_CONFIG:
                return  # Silent the exception below on during testing
            else:
                raise TahoeConfigurationException(
                    'Missing `css_overrides_file` from SiteConfiguration for `{site}` config_id=`{id}`'.format(
                        site=self.site.domain,
                        id=self.site_config.id,
                    )
                )

        storage = self.get_customer_themes_storage()
        with storage.open(file_name, 'w') as f:
            f.write(css_output)

    def get_css_url(self):
        storage = self.get_customer_themes_storage()
        return storage.url(self.site_config.get_value('css_overrides_file'))

    def get_customer_themes_storage(self):
        storage_class = get_storage_class(settings.DEFAULT_FILE_STORAGE)
        return storage_class(**settings.CUSTOMER_THEMES_BACKEND_OPTIONS)

    def delete_css_override(self):
        css_file = self.site_config.get_value('css_overrides_file')
        if css_file:
            try:
                storage = self.get_customer_themes_storage()
                storage.delete(self.site_config.get_value('css_overrides_file'))
            except Exception:  # pylint: disable=broad-except  # noqa
                logger.warning("Can't delete CSS file {}".format(css_file))

    @beeline.traced('site_config.formatted_sass_variables')
    def formatted_sass_variables(self):
        sass_variables = self.site_config.get_sass_variables()

        if self.api_adapter:
            # Tahoe: Use `SiteConfigAdapter` if available.
            beeline.add_context_field('value_source', 'site_config_service')
            sass_variables = self.api_adapter.get_amc_v1_theme_css_variables()
            # Note: css variables from adapter is in dict format
            formatted_sass_variables = ""
            for key, val in sass_variables.items():
                formatted_sass_variables += "{}: {};".format(key, val)
            return formatted_sass_variables

        return " ".join(["{}: {};".format(var, val[0]) for var, val in sass_variables])

    def _sass_var_override(self, path):
        if 'branding-basics' in path:
            return [(path, self.formatted_sass_variables())]
        if 'customer-sass-input' in path:
            return [(path, self.site_config.get_value('customer_sass_input', ''))]
        return None
