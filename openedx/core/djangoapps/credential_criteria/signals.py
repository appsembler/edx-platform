"""
Signal handlers for credential_criteria Django app.
Implement logic to determine if criteria for a Credential have been satisfied
by the event represented in the Signal.
"""

# For initial implementation, we only handle course completion via Aggregator
# but we also may need to handle other events which might affect the Criteria

import logging

from django.dispatch import Signal, receiver

from . import constants, tasks, util


logger = logging.getLogger(__name__)


SATISFIED_USERCRITERION = Signal(providing_args=["user", "criterion"])


def handle_aggregator_update(sender, **kwargs):
    """
    Check completion credential criteria when completion Aggregators are updated.
    aggregators passed from AggregationUpdater.update() are not Aggregator model objects
    but a dictionary of aggregator blocks by block_key.
    """
    if not util.feature_is_enabled():
        logger.debug(
            "Taking no action on Aggregator completion for {}. "
            "Credential Criteria feature not active".format(aggregator.block_key)
        )
        return

    # satisfy any pertinent CredentialCriterion
    for aggregator in kwargs['aggregators']:
        if util.block_can_confer_credentials(aggregator.block_key):
            logger.debug("Checking credential criteria after Aggregator completion for {}".format(
                aggregator.block_key)
            )
            tasks.satisfy_credential_criterion.delay(constants.CREDENTIAL_CRITERION_TYPE_COMPLETION,
                **{"user": aggregator.user, "locator": aggregator.block_key})


@receiver(SATISFIED_USERCRITERION) 
def handle_satisfied_usercredentialcriterion(sender, **kwargs):
    """
    Evaluate any full CredentialCriteria for satisfaction when saving a satisfied UserCredentialCriterion.
    """
    criteria = kwargs['criterion'].criteria
    criteria.evaluate_for_user(kwargs['user'])
