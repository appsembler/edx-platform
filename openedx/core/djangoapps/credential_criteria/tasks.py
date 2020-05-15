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
    user = kwargs['user']
    del kwargs['user']
    criterion_model = criterion_types.get_model_for_criterion_type(criterion_type)
    criterions = criterion_model.model_class().objects.filter(
        criterion_type=criterion_type, **kwargs)
    if not criterions:
        return

    # find an existing user criterions satisfied for this type
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

        criterion.satisfy_for_user(user)  # doesn't necessarily mean it is satisfied


@task(routing_key=settings.CREDENTIAL_CRITERIA_ROUTING_KEY)
def award_credential_for_user(credential_id, **kwargs):
    """
    Contact Credentials service to award the credential to the user.
    """
