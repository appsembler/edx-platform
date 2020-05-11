"""
Models for credentials criteria.
"""

import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.models import TimeStampedModel
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey

from . import constants, exceptions


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
    A collection of criteria sufficient to award a Credential.
    """
    is_active = models.BooleanField()
    credential_id = models.PositiveIntegerField()  # the db id of the Credential in Credentials service
    criteria_narrative = models.TextField()

    class Meta(object):
        abstract = True

    @property
    def criteria_url(self):
        """Implement as a cached property."""
        raise NotImplementedError

    def is_satisfied(self, user):
        """
        Return True only if all related CredentialCriterion are True for the given user
        """
        if not self.is_active():
            return False

        criterion_set = self.criterion_set.all()
        if not criterion_set:
            msg = "Cannot evalute credential criteria: no member criterion"
            raise exceptions.CredentialCriteriaException(msg, user)

        satisfied = True
        for crit in criterion_set:
            # an exception will also mean criteria are not satisfied
            if not crit.is_satisfied():
                satisfied = False
                logger.debug("Criterion {} not satisfied for {}".format(crit, user))
                break
        return satisfied

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
        # store as a UserCredentialAttribute
        raise NotImplementedError

    class Meta(object):
        verbose_name = "Badge Criteria"


class CredentialCriterion(TimeStampedModel):
    """
    A single criterion making up part of the CredentialCriteria.
    Each criterion type must have a corresponding logic to determine
    satisfaction of the criterion.
    """
    criterion_type = models.CharField(values=constants.CREDENTIAL_CRITERION_TYPES)
    satisfaction_threshold = models.FloatField(min=0.0, max=1.0)  # not sure about min/max
    criteria = models.GenericForeignKey(CredentialCriteria)

    class Meta(object):
        abstract = True

    @property
    def criterion_class(self):
        return getattr(criterion, self.criterion_type + 'CriterionType')

    def is_satisfied(self):
        try:
            return self.criterion_class.is_satisfied(user, self)
        except Exception as e:
            raise exceptions.CredentialCriteriaException(e.msg, user)


class CredentialUsageKeyCriterion(CredentialCriterion):
    """
    A single criterion based on score for a given set of opaque_keys.edx.keys.UsageKey
    Can be based on either learner's grade or completion percentage.
    """
    block_id = models.UsageKeyField()
