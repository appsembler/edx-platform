"""
Models for credentials criteria.
"""

import logging

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.models import TimeStampedModel
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey

from . import constants, criterion_types, exceptions, signals, tasks


logger = logging.getLogger(__name__)


def _choices(*values):
    """
    Helper for use with model field 'choices'.
    """
    return [(value,) * 2 for value in values]


def validate_course_key(course_key):
    """
    Validate the course_key is correct.
    """
    try:
        CourseKey.from_string(course_key)
    except InvalidKeyError:
        raise ValidationError(_("Invalid course key."))


def validate_usage_key(usage_key):
    """
    Validate the usage_key is correct.
    """
    try:
        UsageKey.from_string(usage_key)
    except InvalidKeyError:
        raise ValidationError(_("Invalid usage key."))


class CredentialCriteria(TimeStampedModel):
    """
    A collection of criteria sufficient to award a specific Credential.
    More than one CredentialCriteria can be used for one Credential.
    """
    is_active = models.BooleanField()
    credential_id = models.PositiveIntegerField()  # the db id of the Credential in Credentials service
    criteria_narrative = models.TextField()

    class Meta(object):
        abstract = True

    @property
    def criteria_url(self):
        """Implement as a cached property."""
        return "https://criteria_url.foo"
        # TODO: raise NotImplementedError

    def evaluate_for_user(self, user):
        """
        Award the linked Credential if satisfied for user.
        """
        if self.is_satisfied_for_user(user):
            # TODO: logic for whether it's already been awarded?
            # or let Credentials handle that?
            # we should minimize inter-service communication but 
            # Credentials does store UserCredential so it knows
            self.award_for_user(user)

    def award_for_user(self, user):
        """
        Contact the Credentials Service to award the credential.
        """
        # do awarding
        # pass anything needed for UserCredentialAttribute
        #  - store a reference to the Criteria and its timestamp 
        #    as a UserCredentialAttribute
        # use a Celery task
        tasks.award_credential_for_user(
            user=self.user,
            cred=self.credential_id,
            criteria_narr=self.criteria_narrative,
            criteria_url=self.criteria_url,
            evidence_narr=self.evidence_narrative,
            evidence_url=self.generate_evidence_url()
        ).delay()

    # TODO: think about caching/ cache invalidation
    # would avoid needing to create a UserCredentialCriteria model, too
    # though that's an option
    def is_satisfied_for_user(self, user):
        """
        Return True only if all related CredentialCriterion are True for the given user
        """
        if not self.is_active():  # never sastified if not active
            return False

        # TODO: this needs to be generic
        criterion_set = self.criterion_set.all()
        if not criterion_set:
            msg = "Cannot evalute credential criteria: no member criterion"
            raise exceptions.CredentialCriteriaException(msg, user)

        return all([crit.is_satisfied_for_user(user) for crit in criterion_set])

    def generate_evidence_url(self):
        raise NotImplementedError


class BadgeCriteria(CredentialCriteria):
    """
    A collection of criteria sufficient to award a Badge.
    OpenBadges spec provides for evidence as a narrative or URL.
    For our purposes, URL should be specific to a user but the narrative could
    be derived from the Badge Class or specific to the criteria used to earn it.
    """
    evidence_narrative = models.TextField()

    def generate_evidence_url(self, user):
        """
        Calculate a URL to evidence for this criteria.
        """
        return "https://evidenceurl.foo"
        # TODO: raise NotImplementedError

    class Meta(object):
        verbose_name = "Badge Criteria"


class AbstractCredentialCriterion(TimeStampedModel):
    """
    A single criterion making up part of the CredentialCriteria.
    Each criterion type must have a corresponding logic to determine
    satisfaction of the criterion.
    """
    criterion_type = models.CharField(values=_choices(constants.CREDENTIAL_CRITERION_TYPES))
    satisfaction_threshold = models.FloatField(min=0.0, max=1.0)  # not sure about min/max
    criteria = models.GenericForeignKey(CredentialCriteria)

    user_criterions = GenericRelation(
        UserCredentialCriterion,
        content_type_field='criterion_content_type',
        object_id_field='criterion_id',
        related_query_name='criterions'
    )

    class Meta(object):
        abstract = True

    @cached_property
    def criteria(self):
        return self.criteria_set.all()

    @property
    def criterion_type_class(self):
        return getattr(criterion_types, self.criterion_type + 'CriterionType')

    def is_satisfied_for_user(self, user):
        return self.user_criterions.filter(user=user, satisfied=True)

    def satisfy_for_user(self, user):
        try:
            satisfied = self.criterion_type_class.is_satisfied_for_user(user, self)
        except Exception as e:
            raise exceptions.CredentialCriteriaException(e.msg, user)
        else:
            ucc, created = self.user_criterions.objects.update_or_create(
                user=user,
                satisfied=satisfied,
                criterion=self,
                criterion_id=self.id
            )
            if created and satisfied:
                # any new satisfied criterion should cause its CredentialCriteria to 
                # be evaluated
                signals.satisfied_usercriterion.send(
                    sender=ucc.__class__,
                    user=user,
                    criterion=ucc.criterion
                )


class CredentialUsageKeyCriterion(AbstractCredentialCriterion):
    """
    A single criterion based on score for a given set of opaque_keys.edx.keys.UsageKey
    Can be based on either learner's grade or completion percentage.
    """
    block_id = models.UsageKeyField()


class UserCredentialCriterion(models.TimeStampedModel):
    """
    Status of user for a criterion.
    TODO: think about how this may become no longer satisfied
    """
    user = models.ForeignKey(User)
    criterion_content_type = models.ForeignKey(
        ContentType, limit_choices_to={'model__in': ('credentialusagekeycriterion',)}
    )
    criterion_id = models.PositiveIntegerField()
    criterion = GenericForeignKey('criterion_content_type', 'criterion_id')
    satisfied = models.BooleanField()

    class Meta(object):
        unique_together = (('user', 'criterion'))
