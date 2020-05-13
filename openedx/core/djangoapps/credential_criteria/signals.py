"""
Signal handlers for credential_criteria Django app.
Implement logic to determine if criteria for a Credential have been satisfied
by the event represented in the Signal.
"""

# For initial implementation, we only handle course completion via Aggregator
# but we also may need to handle other events which might affect the Criteria

import logging

from celery import subtask

import django.dispatch

try:
    from completion_aggregator import models as agg_models, signals
except ImportError:
    pass

from . import constants, tasks, waffle


logger = logging.getLogger(__name__)


satisfied_usercriterion = django.dispatch.Signal(providing_args=["user", "criterion"])


def handle_aggregator_update(aggregator, **kwargs):
    """
    Check completion credential criteria when completion Aggregators are updated.
    """
    import pdb; pdb.set_trace()

    logger.debug("Checking credential criteria after Aggregator completion for {}".format(
        aggregator.block_id)
    )

    if not waffle.credentential_criteria_is_active():
        logger.debug(
            "Taking no action on Aggregator completion for {}. "
            "Credential Criteria feature not active".format(aggregator.block_id)
        )
        return

    # satisfy any pertinent CredentialCriterion
    tasks.satisfy_credential_criterion(
        constants.CREDENTIAL_CRITERION_TYPE_COMPLETION,
        **{"user": aggregator.user, "block_id": aggregator.block_id}
    ).delay(callback=subtask(tasks.evaluate_credential_criteria))


def handle_new_usercredentialcriterion(sender, **kwargs):
    """
    Evaluate any full CredentialCriteria for satisfaction when saving a satisfied UserCredentialCriterion.
    """
    criteria = kwargs['criterion'].criteria
    criteria.evaluate_for_user(kwargs['user'])
