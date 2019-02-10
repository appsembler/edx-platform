"""
Badge Awarding backend for Badgr-Server.
"""
import json
import logging
import mimetypes

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from lazy import lazy
from requests.packages.urllib3.exceptions import HTTPError

from badges.backends.base import BadgeBackend
from badges.models import BadgeAssertion
from eventtracking import tracker

MAX_SLUG_LENGTH = 255
LOGGER = logging.getLogger(__name__)


class BadgrBackend(BadgeBackend):
    """
    Backend for Badgr-Server by Concentric Sky. http://info.badgr.io/
    """
    badges = []

    def __init__(self):
        super(BadgrBackend, self).__init__()
        if not settings.BADGR_API_TOKEN:
            raise ImproperlyConfigured("BADGR_API_TOKEN not set.")

    @lazy
    def _base_url(self):
        """
        Base URL for all API requests.
        """
        return "{}/v1/issuer/issuers/{}".format(settings.BADGR_BASE_URL, settings.BADGR_ISSUER_SLUG)

    @lazy
    def _badge_create_url(self):
        """
        URL for generating a new Badge specification
        """
        return "{}/badges".format(self._base_url)

    def _badge_url(self, slug):
        """
        Get the URL for a course's badge in a given mode.
        """
        return "{}/{}".format(self._badge_create_url, slug)

    def _assertion_url(self, slug):
        """
        URL for generating a new assertion.
        """
        return "{}/assertions".format(self._badge_url(slug))

    def _log_if_raised(self, response, data):
        """
        Log server response if there was an error.
        """
        try:
            response.raise_for_status()
        except HTTPError:
            LOGGER.error(
                u"Encountered an error when contacting the Badgr-Server. Request sent to %r with headers %r.\n"
                u"and data values %r\n"
                u"Response status was %s.\n%s",
                response.request.url, response.request.headers,
                data,
                response.status_code, response.content
            )
            raise

    def _create_badge(self, badge_class):
        """
        Create the badge class on Badgr.
        """
        image = badge_class.image
        # We don't want to bother validating the file any further than making sure we can detect its MIME type,
        # for HTTP. The Badgr-Server should tell us if there's anything in particular wrong with it.
        content_type, __ = mimetypes.guess_type(image.name)
        if not content_type:
            raise ValueError(
                u"Could not determine content-type of image! Make sure it is a properly named .png file. "
                u"Filename was: {}".format(image.name)
            )
        files = {'image': (image.name, image, content_type)}
        try:  # TODO: eventually we should pass both
            URLValidator(badge_class.criteria)
            criteria_type = 'criteria_url'
        except ValidationError:
            criteria_type = 'criteria_text'
        data = {
            'name': badge_class.display_name,
            criteria_type: badge_class.criteria,
            'description': badge_class.description,
        }
        result = requests.post(
            self._badge_create_url, headers=self._get_headers(), data=data, files=files,
            timeout=settings.BADGR_TIMEOUT
        )
        self._log_if_raised(result, data)

    def _send_assertion_created_event(self, user, assertion):
        """
        Send an analytics event to record the creation of a badge assertion.
        """
        tracker.emit(
            'edx.badge.assertion.created', {
                'user_id': user.id,
                'badge_slug': assertion.badge_class.slug,
                'badge_name': assertion.badge_class.display_name,
                'issuing_component': assertion.badge_class.issuing_component,
                'course_id': unicode(assertion.badge_class.course_id),
                'enrollment_mode': assertion.badge_class.mode,
                'assertion_id': assertion.id,
                'assertion_image_url': assertion.image_url,
                'assertion_json_url': assertion.assertion_url,
                'issuer': assertion.data.get('issuer'),
            }
        )

    def _create_assertion(self, badge_class, user, evidence_url):
        """
        Register an assertion with the Badgr server for a particular user for a specific class.
        """
        data = {
            'email': user.email,
            'evidence': evidence_url,
        }
        response = requests.post(
            self._assertion_url(badge_class.slug), headers=self._get_headers(), data=data,
            timeout=settings.BADGR_TIMEOUT
        )
        self._log_if_raised(response, data)
        assertion, __ = BadgeAssertion.objects.get_or_create(user=user, badge_class=badge_class)
        assertion.data = response.json()
        assertion.backend = 'BadgrBackend'
        assertion.image_url = assertion.data['image']
        assertion.assertion_url = assertion.data['json']['id']
        assertion.save()
        self._send_assertion_created_event(user, assertion)
        return assertion

    def _get_v2_auth_token(self):
        """ Get a Badgr v2 auth token from cache or generate and return a new one.
        """
        cache = settings.CACHES['default']
        cache_key = 'badgr_api_auth_token'
        cached = cache.get(cache_key)
        if cached:
            return cached
        else:
            # get a new auth token using Badgr refresh token
            data = json.dumps({'grant_type': 'refresh_token', 'refresh_token': settings.BADGR_API_TOKEN})
            response = requests.post(self._badge_url(slug), data=data, timeout=settings.BADGR_TIMEOUT)
            if response.ok:
                token = response.data.get('access_token')
                cache.set(cache_key, token, getattr(settings, 'BADGR_API_TOKEN_EXPIRATION', 86400))  #24h
                return token
            else:
                rseponse.raise_for_status()

    def _get_headers(self):
        """
        Headers to send along with the request-- used for authentication.
        """
        # if using v2 or later Badgr API get new auth token if expired
        if settings.BADGR_API_VERSION == 'v1':
            return {'Authorization': 'Token {}'.format(settings.BADGR_API_TOKEN)}
        else:
            return {'Authorization': 'Bearer {}'.format(self._get_v2_auth_token())}

    def _ensure_badge_created(self, badge_class):
        """
        Verify a badge has been created for this badge class, and create it if not.
        """
        slug = badge_class.slug
        if slug in BadgrBackend.badges:
            return
        response = requests.get(self._badge_url(slug), headers=self._get_headers(), timeout=settings.BADGR_TIMEOUT)
        if response.status_code != 200:
            self._create_badge(badge_class)
        BadgrBackend.badges.append(slug)

    def award(self, badge_class, user, evidence_url=None):
        """
        Make sure the badge class has been created on the backend, and then award the badge class to the user.
        """
        self._ensure_badge_created(badge_class)
        return self._create_assertion(badge_class, user, evidence_url)
