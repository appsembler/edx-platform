from social_core.backends.oauth import OAuthAuth
from social_django.strategy import DjangoStrategy

from third_party_auth.models import OAuth2ProviderConfig
from tahoe_idp.api import get_studio_site_configuration


class StudioConfigurationModelStrategy(DjangoStrategy):
    def setting(self, name, default=None, backend=None):
        """
        Load from configuration if possible
        """
        if isinstance(backend, OAuthAuth):
            provider_config = OAuth2ProviderConfig.current(backend.name)
            if not provider_config.is_tahoe_idp_enabled(
                site_configuration=get_studio_site_configuration()
            ):
                raise Exception("Can't fetch setting of a disabled backend/provider.")
            try:
                return provider_config.get_setting(name)
            except KeyError:
                pass
        return super(StudioConfigurationModelStrategy, self).setting(name, default, backend)
