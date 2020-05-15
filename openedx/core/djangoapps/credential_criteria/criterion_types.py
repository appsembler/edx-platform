"""
Logic for calculating satisfaction of a CredentialCriterion,
based on criterion_type; e.g., completion, score, etc..
"""

from abc import ABCMeta, abstractmethod

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured

from completion.models import BlockCompletion
try:
    from completion_aggregator.models import Aggregator
    completion_aggregator_installed = True
except ImportError:
    completion_aggregator_installed = False

from xblock.completable import XBlockCompletionMode
from xblock.core import XBlock
from xblock.plugin import PluginMissingError

from . import constants, exceptions


def get_model_for_criterion_type(criterion_type):
    """
    Return the AbstractCredentialCriterion subclass model which 
    is used for this criterion_type.
    """
    if criterion_type in (
        constants.CREDENTIAL_CRITERION_TYPE_COMPLETION,
        constants.CREDENTIAL_CRITERION_TYPE_SCORE,
        constants.CREDENTIAL_CRITERION_TYPE_GRADE,
        constants.CREDENTIAL_CRITERION_TYPE_PASSFAIL,
        constants.CREDENTIAL_CRITERION_TYPE_ENROLLMENT,
        constants.CREDENTIAL_CRITERION_TYPE_CREDENTIAL
    ):
        # there may be some other cases to support later, like multiple locators,
        # block type, etc.  
        model_name = 'CredentialLocatorCriterion'
    else:
        raise NotImplementedError
    try:
        return ContentType.objects.get(app_label="credential_criteria", model=model_name)
    except ContentType.DoesNotExist:
        raise exception.CredentialCriteriaException(
            "No credential criterion database model found for {}".format(criterion_type)
        )


class AbstractCriterionType(object):
    """
    Abstract class for a criterion type class.
    """
    __metaclass__ = ABCMeta

    @classmethod
    def is_satisfied_for_user(cls, user, credential_criterion):
        raise NotImplementedError


class CompletionCriterionType(AbstractCriterionType):
    """
    Calculate satisfaction of a criterion based on a completion threshold.
    """

    @classmethod
    def _can_use_aggregator(cls, block_type):
        """
        Raise an exception if Completion Aggregaton cannot be used for an aggregator type
        """
        err_msg = None
        if not completion_aggregator_installed:
            err_msg = "completion_aggregator must be installed to compute completion criterion for {}"
        try:
            aggregated_block_types = settings.COMPLETION_AGGREGATOR_BLOCK_TYPES
        except AttributeError:
            err_msg = "Completion Aggregation must be configured in settings to compute completion criterion for {}"
        else:
            if block_type not in settings.COMPLETION_AGGREGATOR_BLOCK_TYPES:
                err_msg = "Completion Aggregation must be configured for {} to compute completion criterion"
        if err_msg:
            raise ImproperlyConfigured(err_msg.format(str(block_type)))

    @classmethod
    def is_satisfied_for_user(cls, user, credential_criterion):
        """
        If BlockCompletion or Aggregator percentage is above the threshold,
        return True.
        """
        crit = credential_criterion
        try:
            block_type = crit.locator.block_type
        except AttributeError:
            raise ValueError("{} is not a completable block".format(crit.locator))

        try:
            mode = XBlockCompletionMode.get_mode(XBlock.load_class(block_type))
        except PluginMissingError:
            # Do not count blocks that aren't registered
            mode = XBlockCompletionMode.EXCLUDED

        if mode not in (XBlockCompletionMode.COMPLETABLE, XBlockCompletionMode.AGGREGATOR):
            raise ValueError("{} is not a completable block".format(crit.locator))

        if mode == XBlockCompletionMode.AGGREGATOR:
            try:
                CompletionCriterionType._can_use_aggregator(block_type)
            except ImproperlyConfigured as e:
                raise exceptions.CredentialCriteriaException(e.msg, user)
            completion_model = Aggregator
            cmp_field = 'percent'
        else:
            completion_model = BlockCompletion
            cmp_field = 'completion'

        try:
            cmp_obj = completion_model.objects.get(user=user, block_key=crit.locator)
            completion = getattr(cmp_obj, cmp_field)
            return completion >= crit.satisfaction_threshold
        except completion_model.DoesNotExist:
            return False
