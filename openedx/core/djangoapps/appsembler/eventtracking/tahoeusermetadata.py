"""
Event-tracking additions for Tahoe customer-specific metadata.

Custom event-tracking Processor to add properties to events.
"""

from json.decoder import JSONDecodeError
import logging

from celery import task
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError

from . import app_variant, utils


logger = logging.getLogger(__name__)


# can't set this via settings because of plugin signals init prior to settings availability
PREFETCH_TAHOE_USERMETADATA_CACHE_QUEUE = 'edx.core.high_mem'


class TahoeUserProfileMetadataCache(object):
    """Cache metadata from UserProfile."""

    # TODO: rework as a singleton.

    CACHE_NAME = "tahoe_userprofile_metadata_cache"  # can't get from settings here
    CACHE_PREFILLING_KEY = "PREFILLING"
    READY = False
    cache = None

    def ready(self):
        """Finish initializing once cache is created via appsembler.settings plugin_settings."""
        try:
            self.cache = caches[self.CACHE_NAME]
            self.READY = True
        except (KeyError, InvalidCacheBackendError):
            logger.warning(
                "Could not find tahoe_userprofile_metadata_cache."
                "Could be using settings like tutor_staticassets."
            )
            self.READY = False

    def prefill(self):
        """Prefill if not already prefilling."""
        if not self.READY:
            logger.info("Cannot prefill Tahoe UserProfile metadata cache, cache not ready.")
            return
        if self.cache.get(self.CACHE_PREFILLING_KEY):
            # don't allow more than one prefill!
            logger.info("TahoeUserProfileMetadataCache already prefilling")
            return

        self.cache.set(self.CACHE_PREFILLING_KEY, True)
        logger.info("START Prefilling Tahoe UserProfile Metadata Cache...")

        from student.models import UserProfile

        for up in UserProfile.objects.all().select_related('user'):
            self.cache.set(up.user.id, up.get_meta().get('tahoe_idp_metadata', {}), True)

        self.cache.set(self.CACHE_PREFILLING_KEY, False)
        logger.info("FINISH Prefilling Tahoe UserProfile Metadata Cache")

    def get_by_user_id(self, user_id):
        if not self.READY:
            return None
        val = self.cache.get(user_id)
        if val:
            logger.debug(
                'Retrieved UserProfile metadata from cache for user id {} with value {}'.format(
                    user_id, val
                )
            )
        return val

    def set_by_user_id(self, user_id, val, is_prefill=False):
        if not self.READY and not is_prefill:
            # we can set as part of the prefill before done, but not otherwise
            return
        self.cache.set(user_id, val)
        logger.debug('Set and retrieved for user id {} with value {}'.format(
            user_id, self.cache.get(user_id)
        ))

    def invalidate(self, instance):
        # called by signal handler on post_save, post_delete of UserProfile
        # we can invalidate even while prefilling as long as key is found
        # TODO: if this is a save and not delete, we should set the new value
        if self.READY:
            self.cache.delete(instance.user_id)


# import of settings is a problem when creating this via plugin architecture
@task(routing_key=PREFETCH_TAHOE_USERMETADATA_CACHE_QUEUE)
def prefetch_tahoe_usermetadata_cache(cache_instance):
    """Celery task to prefill the TahoeUserProfileMetadataCache.

    Will run on the worker's instance of the cache.
    Designed to work with a shared cache like memcached.
    """
    cache_instance.prefill()


class TahoeUserMetadataProcessor(object):
    """
    Event tracking Processor for Tahoe User Data.

    Always returns the event for continued processing.
    """

    def _get_reg_metadata_from_cache(self, user_id):
        cached = userprofile_metadata_cache.get_by_user_id(user_id)
        if cached:
            return cached
        else:
            return {}

    def _get_idp_metadata_from_tpa_pipeline(self):
        """Check ThirdPartyAuth pipeline for details containing IdP metadata."""
        import crum
        from third_party_auth import pipeline
        try:
            request = crum.get_current_request()
            tpa_running = pipeline.running(request)
            if not tpa_running:
                return None
            tpa = pipeline.get(request)
            details = tpa['kwargs'].get('details')
            return details.get('tahoe_idp_metadata', {})
        except:
            return None

    def _get_custom_registration_metadata(self, user_id):
        """
        Get any custom registration field data for the User.

        Retrieved from the `registration_additional` property of `tahoe_idp_metadata`.
        Returns a dictionary.
        """
        # look in cache first
        cached_metadata = self._get_reg_metadata_from_cache(user_id)
        reg_additional = cached_metadata.get('registration_additional')
        if reg_additional:
            return reg_additional

        # local import, as module is loaded at startup via eventtracking.django for Processor init
        from student.models import UserProfile
        try:
            profile = UserProfile.objects.get(user__id=user_id)
        except UserProfile.DoesNotExist:
            return {}
        else:
            meta = profile.get_meta()
            idp_metadata = meta.get("tahoe_idp_metadata", {})
            if not idp_metadata:
                logger.info("User {user_id} has no IDP metadata yet".format(user_id=user_id))
                # We could be processing an event (e.g., course enrollment) on very first User.save()
                # This can happen  before UserProfile has been updated via tahoe_idp TPA step.
                # Try getting it direclty from TPA pipeline.
                idp_metadata = self._get_idp_metadata_from_tpa_pipeline()
                if not idp_metadata:
                    return {}
        custom_reg_data = idp_metadata.get("registration_additional")
        userprofile_metadata_cache.set_by_user_id(user_id, idp_metadata)
        return custom_reg_data

    def _get_user_tahoe_metadata(self, user_id):
        """Build additional tracking context from Tahoe IDP metadata about the user."""
        # for now we only get custom registration field values
        try:
            custom_reg_data = self._get_custom_registration_metadata(user_id)
        except JSONDecodeError:
            logger.info("Bad JSON in UserProfile.meta for user id {}".format(user_id))
            return {"ERROR": "Cannot return User metadata due to invalid JSON."}

        # there may eventually be others we want to add as event context,
        # in which case any value should be returned
        if custom_reg_data:
            return {"registration_extra": custom_reg_data}
        else:
            return {}

    def __call__(self, event):
        """Process the event and return the event."""
        # WARNING:
        # We have to be careful to not add SQL queries that would require updating upstream tests
        # which count SQL queries; e.g., `cms.djangoapps.contentstore.views.tests.test_course_index)
        # We should not let this run in any CMS tests and any LMS tests other than from
        # within openedx/core/djangoapps/eventtracking/  Ugh.
        # We don't care about user metadata for Studio, at this point.
        # Allow to run in LMS or it's own LMS env tests.
        if not app_variant.is_lms():  # this returns False if a test in LMS
            if app_variant.is_test():
                if not app_variant.is_self_test():  # expensive, make sure it's a test first.
                    return event
            else:
                return event

        # eventtracking Processors are loaded before apps are ready
        from django.contrib.auth.models import User

        # Don't try to get the user from the request:  it could be an instructor doing
        # a bulk enrollment or exception certificate triggering the event.  Only use the
        # user from event itself.

        try:
            user_id = utils.get_user_id_from_event(event)
        except AttributeError:
            logger.debug(
                "TahoeUserMetadataProcessor passed invalid type to "
                "get_user_id_from_event: {}. Likely innocuous. "
                "Logging and continuing.".format(event)
            )
        else:
            if user_id:
                # Add any Tahoe metadata context
                tahoe_user_metadata = self._get_user_tahoe_metadata(user_id)
                if tahoe_user_metadata:
                    event['context']['tahoe_user_metadata'] = tahoe_user_metadata
        finally:
            return event


userprofile_metadata_cache = TahoeUserProfileMetadataCache()
