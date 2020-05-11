"""
Logic for calculating satisfaction of a CredentialCriterion,
based on criterion_type.
"""

from django.conf import settings
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

from . import exceptions


class AbstractCriterionType(AbstractBaseClass):
    """
    Abstract class for a criterion type class.
    """

    def is_satisfied(self, user, credential_criterion):
        raise NotImplementedError


class CompletionCriterionType(AbstractCriterion):
    """
    Calculate satisfaction of a criterion based on a completion threshold.
    """

    def _can_use_aggregator(self, block_type):
        """
        Raise an exception if Completion Aggregaton cannot be used for an aggregator type
        """
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

    def is_satisfied(self, user, credential_criterion):
        """
        If BlockCompletion or Aggregator percentage is above the threshold,
        return True.
        """
        crit = credential_criterion
        block_type = crit.block_id.block_type

        try:
            mode = XBlockCompletionMode.get_mode(XBlock.load_class(block_type))
        except PluginMissingError:
            # Do not count blocks that aren't registered
            mode = XBlockCompletionMode.EXCLUDED

        if mode not in (XBlockCompletionMode.COMPETABLE, XBlockCompletionMode.AGGREGATOR):
            raise ValueError("{} is not a completable block".format(crit.block_id))

        if mode == XBlockCompletionMode.AGGREGATOR:
            try:
                self._can_use_aggregator(block_type)
            except ImproperlyConfigured as e:
                raise exceptions.CredentialCriteriaException(e.msg, user)
            completion_model = Aggregator
        else:
            completion_model = BlockCompletion

        try:
            cmp_obj = completion_model.objects.get(user=user, block_key=crit.block_id)
            completion = getattr(cmp_obj, cmp_field)
            return completion >= crit.satisfaction_threshold
        except completion_model.DoesNotExist:
            return False
