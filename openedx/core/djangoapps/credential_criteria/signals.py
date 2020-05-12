"""
Signal handlers for credential_criteria Django app.
Implement logic to determine if criteria for a Credential have been satisfied
by the event represented in the Signal.
"""

# For initial implementation, we only handle course completion via Aggregator
# but we also may need to handle other events which might affect the Criteria

import logging

from django.conf import settings

from xmodule.modulestore.django import SignalHandler

try:
    from completion_aggregator import models as agg_models, signals
except ImportError:
    pass

from . import criterion, models, tasks


logger = logging.getLogger(__name__)


def register():
    """
    Register signal handlers.
    Do this here since we can't assume completion_aggregator is installed.
    """
    signals.aggregator_updated.connect(aggregator_updated_handler, sender=agg_models.AggregatorUpdater)


# Signal handlers frequently ignore arguments passed to them.  No need to lint them.
# pylint: disable=unused-argument

def aggregator_updated_handler(aggregator, **kwargs):
    """
    Check completion credential criteria when completion Aggregators are updated.
    """

    logger.debug("Checking credential criteria after Aggregator completion for {}".format(
        aggregator.block_id)
    )
    # do some more stuff
    criterion  # pylint
    models  # pylint
    tasks  # pylint
