"""
Celery tasks for credential_criteria Django app.
"""

import logging

from celery import task

from django.conf import settings

from . import criterion_types
from .models import UserCredentialCriterion


logger = logging.getLogger(__name__)


@task(routing_key=settings.CREDENTIAL_CRITERIA_ROUTING_KEY, ignore_result=True)
def satisfy_credential_criterion(criterion_type, **kwargs):
    # satisfy any pertinent CredentialCriterion
    user = kwargs['user']
    del kwargs['user']
    criterion_model = criterion_types.get_model_for_criterion_type(criterion_type)
    criterions = criterion_model.model_class().objects.filter(
        criterion_type=criterion_type, **kwargs)
    if not criterions:
        return

    # find any existing user criterions satisfied for this type
    user_satisfied = UserCredentialCriterion.objects.filter(
        user=user, criterion_content_type=criterion_model,
        satisfied=True).values_list('criterions', flat=True).distinct()

    for criterion in criterions:
        try:
            if criterion.id in user_satisfied:
                # any already satisfied don't need to be rechecked
                continue
        except AttributeError:
            pass  # no user_satisfied

        # see if the criterion is satisfied for this user
        criterion.satisfy_for_user(user)


@task(routing_key=settings.CREDENTIAL_CRITERIA_ROUTING_KEY, ignore_result=True)
def award_credential_for_user(**kwargs):
    """
    Contact Credentials service to award the credential to the user.
    """
    logger.info("Contacting Credentials service to award {} for {}".format(
        kwargs['credential_id'], kwargs['user'])
    )
    # eventually we should notify the user based on the task result
