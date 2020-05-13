"""
Credentials Criteria
"""

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from openedx.core.djangoapps.plugins.constants import ProjectType, SettingsType, PluginSettings, PluginSignals


class CredentialsConfig(AppConfig):
    """
    Configuration class for credentials Django app
    """
    name = 'openedx.core.djangoapps.credential_criteria'
    verbose_name = _("Credential Criteria")

    plugin_app = {
        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                SettingsType.AWS: {PluginSettings.RELATIVE_PATH: u'settings.aws'},
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: u'settings.common'},
                SettingsType.DEVSTACK: {PluginSettings.RELATIVE_PATH: u'settings.devstack'},
                SettingsType.TEST: {PluginSettings.RELATIVE_PATH: u'settings.test'},
            }
        },
        PluginSignals.CONFIG: {
            ProjectType.LMS: {
                PluginSignals.RECEIVERS: [
                    # just handling completion-based for now
                    {
                        PluginSignals.RECEIVER_FUNC_NAME: u'handle_aggregator_update',
                        PluginSignals.SIGNAL_PATH: u'completion_aggregator.signals.AGGREGATORS_UPDATED',
                    },
                    {
                        PluginSignals.RECEIVER_FUNC_NAME: u'handle_aggregator_update',
                        PluginSignals.SIGNAL_PATH: u'django.db.models.signals.post_save',
                        PluginSignals.SENDER: u'completion_aggregator.models.Aggregator',
                    },
                    {
                        PluginSignals.RECEIVER_FUNC_NAME: u'handle_blockcompletion_update',
                        PluginSignals.SIGNAL_PATH: u'django.db.models.signals.post_save',
                        PluginSignals.SENDER: u'completion.models.BlockCompletion',
                    },

                ],
            },
        },
    }

    def ready(self):
        # Register celery workers
        from . import tasks  # pylint: disable=unused-variable
