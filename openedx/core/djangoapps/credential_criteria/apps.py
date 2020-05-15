"""
Credentials Criteria
"""

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from openedx.core.djangoapps.plugins.constants import ProjectType, SettingsType, PluginSettings, PluginSignals


class CredentialCriteriaConfig(AppConfig):
    """
    Configuration class for credential_criteria Django app
    """
    name = 'openedx.core.djangoapps.credential_criteria'
    verbose_name = _("Credential Criteria")

    plugin_app = {
        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                SettingsType.AWS: {PluginSettings.RELATIVE_PATH: u'settings.aws'},
                SettingsType.COMMON: {PluginSettings.RELATIVE_PATH: u'settings.common'},
                # SettingsType.DEVSTACK: {PluginSettings.RELATIVE_PATH: u'settings.devstack'},
                # SettingsType.TEST: {PluginSettings.RELATIVE_PATH: u'settings.test'},
            }
        },
        PluginSignals.CONFIG: {
            ProjectType.LMS: {
                PluginSignals.RECEIVERS: [
                    # just handling completion-based for now
                    {
                        PluginSignals.RECEIVER_FUNC_NAME: u'handle_aggregator_update',
                        PluginSignals.SIGNAL_PATH: u'completion_aggregator.signals.AGGREGATORS_UPDATED',
                        PluginSignals.SENDER_PATH: u'completion_aggregator.core.AggregationUpdater',
                    },
                    {
                        PluginSignals.RECEIVER_FUNC_NAME: u'handle_satisfied_usercredentialcriterion',
                        PluginSignals.SIGNAL_PATH: u'openedx.core.djangoapps.credential_criteria.signals.SATISFIED_USERCRITERION',
                    },
                    # the post_save should only send a single Aggregator object
                    # {
                    #     PluginSignals.RECEIVER_FUNC_NAME: u'handle_aggregator_update',
                    #     PluginSignals.SIGNAL_PATH: u'django.db.models.signals.post_save',
                    #     PluginSignals.SENDER_PATH: u'completion_aggregator.models.Aggregator',
                    # },
                    # {
                    #     PluginSignals.RECEIVER_FUNC_NAME: u'handle_blockcompletion_update',
                    #     PluginSignals.SIGNAL_PATH: u'django.db.models.signals.post_save',
                    #     PluginSignals.SENDER_PATH: u'completion.models.BlockCompletion',
                    # },

                ],
            },
        },
    }

    def ready(self):
        # Register celery workers
        from . import tasks  # pylint: disable=unused-variable
