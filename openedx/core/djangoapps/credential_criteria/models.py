"""
Models for credentials criteria.
"""

import itertools
import logging

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.models import TimeStampedModel
from opaque_keys import InvalidKeyError

try:
    from opaque_keys.edx.keys import LearningContextKey
    from opaque_keys.edx.django.models import LearningContextKeyField
    model_keyfield_type = LearningContextKeyField
    model_key_class = LearningContextKey
except ImportError:
    from opaque_keys.edx.keys import UsageKey
    from opaque_keys.edx.django.models import UsageKeyField
    model_keyfield_type = UsageKeyField
    model_key_class = UsageKey

from . import constants, criterion_types, exceptions


logger = logging.getLogger(__name__)


def _choices(*values):
    """
    Helper for use with model field 'choices'.
    """
    return [[value, value] for value in values]


def validate_locator_field(key):
    """
    Validate the usage_key is correct.
    """
    try:
        locator = model_key_class.from_string(key)
    except InvalidKeyError:
        raise ValidationError(_("Invalid {}".format(key.KEY_TYPE)))
    else:
        from . import settings
        if locator.block_type not in settings.CREDENTIAL_CONFERRING_BLOCK_TYPES:  # this can't be Site aware
            raise ValidationError(_("{} cannot be used as criteria for credentials".format(locator.block_type)))


class CredentialCriteria(TimeStampedModel):
    """
    A collection of criteria sufficient to award a specific Credential.
    More than one CredentialCriteria can be used for one Credential.
    """
    is_active = models.BooleanField()
    credential_id = models.PositiveIntegerField()  # the db id of the Credential in Credentials service
    credential_type = models.CharField(max_length=255, choices=_choices('badge', 'coursecertificate', 'programcertificate'))
    # criteria and evidence fields are typically generated but can be set directly
    _criteria_narrative = models.TextField()
    _criteria_url = models.URLField()
    _evidence_narrative = models.TextField()
    _evidence_url = models.URLField()

    @property
    def criteria_url(self):
        """Implement as a cached property."""
        if self._criteria_url:
            return self._criteria_url
        else:
            # TODO: calculate a URL which might be a view that explains criteria
            # using their display names and values
            return "https://criteria_url.foo"

    @criteria_url.setter
    def criteria_url(self, value):
        self._criteria_url = value

    @property
    def criteria_narrative(self):
        return self._criteria_narrative

    @criteria_narrative.setter
    def criteria_narrative(self, value):
        self._criteria_narrative = value

    @property
    def evidence_url(self):
        if self._evidence_url:
            return self._evidence_url
        else:
            # TODO: calculate an evidence url
            # the idea is that the evidence for a credential
            # may be different depending on the award criteria used to achieve it
            return "https://evidence_url.foo"

    @evidence_url.setter
    def evidence_url(self, value):
        self._evidence_url = value

    @property
    def evidence_narrative(self):
        return self._criteria_narrative

    @evidence_narrative.setter
    def evidence_narrative(self, value):
        self._evidence_narrative = value

    @cached_property
    def criterions(self):
        """Get union value of related set from all subclasses of AbstractCredentialCriterion."""
        # using cached_property this is evaluated only once per instance (in memory)
        concretes = [sc.__name__.lower() for sc in AbstractCredentialCriterion.__subclasses__()]
        related_managers = [getattr(self, '{}_set'.format(cname)) for cname in concretes]
        return tuple(itertools.chain(*[list(manager.all()) for manager in related_managers]))

    def __repr__(self):
        return "<CredentialCriteria: awards {credential_type} id {credential_id} active={is_active}>".format(
            credential_type=self.credential_type,
            credential_id=self.credential_id,
            is_active=self.is_active
        )

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
        from .tasks import award_credential_for_user
        award_credential_for_user.delay(**dict(
            user=user,
            credential_id=self.credential_id,
            credential_type=self.credential_type,
            criteria_narrative=self.criteria_narrative,
            criteria_url=self.criteria_url,
            evidence_narrative=self.evidence_narrative,
            evidence_url=self.evidence_url)
        )

    # TODO: think about caching/ cache invalidation
    # would avoid needing to create a UserCredentialCriteria model, too
    # though that's an option
    def is_satisfied_for_user(self, user):
        """
        Return True only if all related CredentialCriterion are True for the given user
        """
        # TODO: what happens when a CredentialCriteria becomes active after?
        # probably shouldn't allow creation of a UserCredentialCriterion for inactive Criteria
        if not self.is_active:  # never sastified if not active
            return False

        if not self.criterions:
            msg = "Cannot evalute credential criteria: no member criterion"
            raise exceptions.CredentialCriteriaException(msg, user)

        return all(crit.is_satisfied_for_user(user) for crit in self.criterions)

    def generate_evidence_url(self):
        raise NotImplementedError


class UserCredentialCriterion(TimeStampedModel):
    """
    Status of user for a criterion.
    TODO: think about how this may become no longer satisfied
    """
    user = models.ForeignKey(User)
    criterion_content_type = models.ForeignKey(
        ContentType, limit_choices_to={'model__in': ('credentiallocatorcriterion',)}
    )
    criterion_id = models.PositiveIntegerField()
    criterion = GenericForeignKey('criterion_content_type', 'criterion_id')
    satisfied = models.BooleanField()

    class Meta(object):
        unique_together = (('user', 'criterion_id'))


class AbstractCredentialCriterion(TimeStampedModel):
    """
    A single criterion making up part of the CredentialCriteria.
    The concrete model subclass provides additional fields relating to the *context*
    of the criterion.  Each criterion *type* has a corresponding logic
    to determine satisfaction of the criterion.

    For example, a criterion with a UsageKey context can be satisfied by a score,
    completion, a letter grade, etc.
    """
    criterion_type = models.CharField(max_length=255, choices=_choices(constants.CREDENTIAL_CRITERION_TYPES))
    satisfaction_threshold = models.FloatField()
    criteria = models.ForeignKey(CredentialCriteria, related_query_name='%(class)ss')

    user_criterions = GenericRelation(
        UserCredentialCriterion,
        content_type_field='criterion_content_type',
        object_id_field='criterion_id',
        related_query_name='criterions'
    )

    class Meta(object):
        abstract = True

    @property
    def criterion_type_class(self):
        return getattr(criterion_types, self.criterion_type.title() + 'CriterionType')

    def is_satisfied_for_user(self, user):
        return self.user_criterions.filter(user=user, satisfied=True).exists()

    def satisfy_for_user(self, user):
        try:
            satisfied = self.criterion_type_class.is_satisfied_for_user(user, self)
        except Exception as e:
            raise exceptions.CredentialCriteriaException(e.msg, user)
        else:
            criterion_content_type=ContentType.objects.get_for_model(self)
            ucc, created = self.user_criterions.update_or_create(
                user=user,
                satisfied=satisfied,
                criterion_content_type=criterion_content_type,
                criterion_id=self.id
            )
            if created and satisfied:
                # any new, satisfied criterion should cause its CredentialCriteria to 
                # be evaluated
                from . import signals
                signals.SATISFIED_USERCRITERION.send(
                    sender=ucc.__class__,
                    user=user,
                    criterion=ucc.criterion
                )


class CredentialLocatorCriterion(AbstractCredentialCriterion):
    """
    A criterion in the context of a single opaque_keys.edx.keys key type
    depending on version of opaque_keys will be OpaqueKey or LearningContextKey
    """
    locator = model_keyfield_type(max_length=255, validators=[validate_locator_field, ])

    class Meta(object):
        verbose_name = '{} Credential Criterion'.format(model_key_class.__name__)

    def __repr__(self):
        return "<CredentialLocatorCriterion: satisfied by {criterion_type} {satisfaction_threshold} for {locator}>".format(
            criterion_type=self.criterion_type,
            satisfaction_threshold=self.satisfaction_threshold,
            locator=self.locator
        )
