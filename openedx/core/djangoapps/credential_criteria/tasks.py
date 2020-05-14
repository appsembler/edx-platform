"""
Celery tasks for credential_criteria Django app.
"""

from celery import task

from django.conf import settings

from . import criterion_types
from .models import UserCredentialCriterion



@task(routing_key=settings.CREDENTIAL_CRITERIA_ROUTING_KEY, ignore_result=True)
def satisfy_credential_criterion(criterion_type, **kwargs):
    # satisfy any pertinent CredentialCriterion
    criterion_model = criterion.get_model_for_criterion_type(criterion_type)
    criterions = criterion_model.objects.filter(
        criterion_type=criterion_type, **kwargs)

    user_satisfied = models.UserCredentialCriterion.objects.filter(
        user=kwargs['user'], criterion__in=criterions,
        satisfied=True).values('criterion')

    for criterion in criterions:
        if criterion in user_satisfied:
            # any already satisfied don't need to be rechecked
            continue

        UserCredentialCriterion.objects.update(
            satisfied=criterion.is_satisfied_for_user(**kwargs),
            user=kwargs['user'], criterion=criterion)


@task(routing_key=settings.CREDENTIAL_CRITERIA_ROUTING_KEY)
def evaluate_credential_criteria(criterion_type, **kwargs):
    """
    Evaluate whether any CredentialCriteria have been met for affected block id.
    Contact Credentials service for award where appropriate.
    """
    # find CredentialCriteria which use criterion of type

    # and then from that CredentialCriteria see if all member CredentialCriterion are satisfied
