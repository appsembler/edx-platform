"""
An API for retrieving user account information.

For additional information and historical context, see:
https://openedx.atlassian.net/wiki/display/TNL/User+API
"""
import datetime
import logging
from functools import wraps
import uuid

import pytz
from django.apps import apps
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, logout
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import transaction
from edx_rest_framework_extensions.authentication import JwtAuthentication
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .api import get_account_settings, update_account_settings
from ..errors import UserNotFound, UserNotAuthorized, AccountUpdateError, AccountValidationError
from openedx.core.lib.api.authentication import (
    SessionAuthenticationAllowInactiveUser,
    OAuth2AuthenticationAllowInactiveUser,
)
from .permissions import CanDeactivateUser, CanReplaceUsername
from openedx.core.lib.api.parsers import MergePatchParser
from student.models import User

log = logging.getLogger(__name__)

class AccountViewSet(ViewSet):
    """
        **Use Cases**

            Get or update a user's account information. Updates are supported
            only through merge patch.

        **Example Requests**

            GET /api/user/v1/me[?view=shared]
            GET /api/user/v1/accounts?usernames={username1,username2}[?view=shared]
            GET /api/user/v1/accounts/{username}/[?view=shared]

            PATCH /api/user/v1/accounts/{username}/{"key":"value"} "application/merge-patch+json"

        **Response Values for GET requests to the /me endpoint**
            If the user is not logged in, an HTTP 401 "Not Authorized" response
            is returned.

            Otherwise, an HTTP 200 "OK" response is returned. The response
            contains the following value:

            * username: The username associated with the account.

        **Response Values for GET requests to /accounts endpoints**

            If no user exists with the specified username, an HTTP 404 "Not
            Found" response is returned.

            If the user makes the request for her own account, or makes a
            request for another account and has "is_staff" access, an HTTP 200
            "OK" response is returned. The response contains the following
            values.

            * bio: null or textual representation of user biographical
              information ("about me").
            * country: An ISO 3166 country code or null.
            * date_joined: The date the account was created, in the string
              format provided by datetime. For example, "2014-08-26T17:52:11Z".
            * email: Email address for the user. New email addresses must be confirmed
              via a confirmation email, so GET does not reflect the change until
              the address has been confirmed.
            * gender: One of the following values:

                * null
                * "f"
                * "m"
                * "o"

            * goals: The textual representation of the user's goals, or null.
            * is_active: Boolean representation of whether a user is active.
            * language: The user's preferred language, or null.
            * language_proficiencies: Array of language preferences. Each
              preference is a JSON object with the following keys:

                * "code": string ISO 639-1 language code e.g. "en".

            * level_of_education: One of the following values:

                * "p": PhD or Doctorate
                * "m": Master's or professional degree
                * "b": Bachelor's degree
                * "a": Associate's degree
                * "hs": Secondary/high school
                * "jhs": Junior secondary/junior high/middle school
                * "el": Elementary/primary school
                * "none": None
                * "o": Other
                * null: The user did not enter a value

            * mailing_address: The textual representation of the user's mailing
              address, or null.
            * name: The full name of the user.
            * profile_image: A JSON representation of a user's profile image
              information. This representation has the following keys.

                * "has_image": Boolean indicating whether the user has a profile
                  image.
                * "image_url_*": Absolute URL to various sizes of a user's
                  profile image, where '*' matches a representation of the
                  corresponding image size, such as 'small', 'medium', 'large',
                  and 'full'. These are configurable via PROFILE_IMAGE_SIZES_MAP.

            * requires_parental_consent: True if the user is a minor
              requiring parental consent.
            * username: The username associated with the account.
            * year_of_birth: The year the user was born, as an integer, or null.
            * account_privacy: The user's setting for sharing her personal
              profile. Possible values are "all_users" or "private".
            * accomplishments_shared: Signals whether badges are enabled on the
              platform and should be fetched.

            For all text fields, plain text instead of HTML is supported. The
            data is stored exactly as specified. Clients must HTML escape
            rendered values to avoid script injections.

            If a user who does not have "is_staff" access requests account
            information for a different user, only a subset of these fields is
            returned. The returns fields depend on the
            ACCOUNT_VISIBILITY_CONFIGURATION configuration setting and the
            visibility preference of the user for whom data is requested.

            Note that a user can view which account fields they have shared
            with other users by requesting their own username and providing
            the "view=shared" URL parameter.

        **Response Values for PATCH**

            Users can only modify their own account information. If the
            requesting user does not have the specified username and has staff
            access, the request returns an HTTP 403 "Forbidden" response. If
            the requesting user does not have staff access, the request
            returns an HTTP 404 "Not Found" response to avoid revealing the
            existence of the account.

            If no user exists with the specified username, an HTTP 404 "Not
            Found" response is returned.

            If "application/merge-patch+json" is not the specified content
            type, a 415 "Unsupported Media Type" response is returned.

            If validation errors prevent the update, this method returns a 400
            "Bad Request" response that includes a "field_errors" field that
            lists all error messages.

            If a failure at the time of the update prevents the update, a 400
            "Bad Request" error is returned. The JSON collection contains
            specific errors.

            If the update is successful, updated user account data is returned.
    """
    authentication_classes = (
        OAuth2AuthenticationAllowInactiveUser, SessionAuthenticationAllowInactiveUser, JwtAuthentication
    )
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MergePatchParser,)

    def get(self, request):
        """
        GET /api/user/v1/me
        """
        return Response({'username': request.user.username})

    def list(self, request):
        """
        GET /api/user/v1/accounts?username={username1,username2}
        """
        usernames = request.GET.get('username')
        try:
            if usernames:
                usernames = usernames.strip(',').split(',')
            account_settings = get_account_settings(
                request, usernames, view=request.query_params.get('view'))
        except UserNotFound:
            return Response(status=status.HTTP_403_FORBIDDEN if request.user.is_staff else status.HTTP_404_NOT_FOUND)

        return Response(account_settings)

    def retrieve(self, request, username):
        """
        GET /api/user/v1/accounts/{username}/
        """
        try:
            account_settings = get_account_settings(
                request, [username], view=request.query_params.get('view'))
        except UserNotFound:
            return Response(status=status.HTTP_403_FORBIDDEN if request.user.is_staff else status.HTTP_404_NOT_FOUND)

        return Response(account_settings[0])

    def partial_update(self, request, username):
        """
        PATCH /api/user/v1/accounts/{username}/

        Note that this implementation is the "merge patch" implementation proposed in
        https://tools.ietf.org/html/rfc7396. The content_type must be "application/merge-patch+json" or
        else an error response with status code 415 will be returned.
        """
        try:
            with transaction.atomic():
                update_account_settings(request.user, request.data, username=username)
                account_settings = get_account_settings(request, [username])[0]
        except UserNotAuthorized:
            return Response(status=status.HTTP_403_FORBIDDEN if request.user.is_staff else status.HTTP_404_NOT_FOUND)
        except UserNotFound:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except AccountValidationError as err:
            return Response({"field_errors": err.field_errors}, status=status.HTTP_400_BAD_REQUEST)
        except AccountUpdateError as err:
            return Response(
                {
                    "developer_message": err.developer_message,
                    "user_message": err.user_message
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(account_settings)


class AccountDeactivationView(APIView):
    """
    Account deactivation viewset. Currently only supports POST requests.
    Only admins can deactivate accounts.
    """
    authentication_classes = (JwtAuthentication, )
    permission_classes = (permissions.IsAuthenticated, CanDeactivateUser)

    def post(self, request, username):
        """
        POST /api/user/v1/accounts/{username}/deactivate/

        Marks the user as having no password set for deactivation purposes.
        """
        user = User.objects.get(username=username)
        user.set_unusable_password()
        user.save()
        account_settings = get_account_settings(request, [username])[0]
        return Response(account_settings)
        _set_unusable_password(User.objects.get(username=username))
        return Response(get_account_settings(request, [username])[0])


class UsernameReplacementView(APIView):
    """
    WARNING: This API is only meant to be used as part of a larger job that
    updates usernames across all services. DO NOT run this alone or users will
    not match across the system and things will be broken.

    API will recieve a list of current usernames and their requested new
    username. If their new username is taken, it will randomly assign a new username.
    """
    authentication_classes = (JwtAuthentication, )
    permission_classes = (permissions.IsAuthenticated, CanReplaceUsername)

    def post(self, request):
        """
        POST /api/user/v1/accounts/replace_usernames/
        {
            "username_mappings": [
                {"current_username_1": "desired_username_1"},
                {"current_username_2": "desired_username_2"}
            ]
        }

        **POST Parameters**

        A POST request must include the following parameter.

        * username_mappings: Required. A list of objects that map the current username (key)
          to the desired username (value)

        **POST Response Values**

        As long as data validation passes, the request will return a 200 with a new mapping
        of old usernames (key) to new username (value)

        {
            "successful_replacements": [
                {"old_username_1": "new_username_1"}
            ],
            "failed_replacements": [
                {"old_username_2": "new_username_2"}
            ]
        }

        TODO: Determine if we need an audit trail outside of logging and API response.
        """

        # (model_name, column_name)
        MODELS_WITH_USERNAME = (
            ('auth.user', 'username'),
            ('consent.DataSharingConsent', 'username'),
            ('consent.HistoricalDataSharingConsent', 'username'),
            ('credit.CreditEligibility', 'username'),
            ('credit.CreditRequest', 'username'),
            ('credit.CreditRequirementStatus', 'username'),
            ('user_api.UserRetirementPartnerReportingStatus', 'original_username'),
            ('user_api.UserRetirementStatus', 'original_username')
        )
        UNIQUE_SUFFIX_LENGTH = getattr(settings, 'SOCIAL_AUTH_UUID_LENGTH', 4)

        username_mappings = request.data.get("username_mappings")
        replacement_locations = self._load_models(MODELS_WITH_USERNAME)

        if not self._has_valid_schema(username_mappings):
            raise ValidationError("Request data does not match schema")

        successful_replacements, failed_replacements = [], []

        for username_pair in username_mappings:
            current_username = list(username_pair.keys())[0]
            desired_username = list(username_pair.values())[0]
            new_username = self._generate_unique_username(desired_username, suffix_length=UNIQUE_SUFFIX_LENGTH)
            successfully_replaced = self._replace_username_for_all_models(
                current_username,
                new_username,
                replacement_locations
            )
            if successfully_replaced:
                successful_replacements.append({current_username: new_username})
            else:
                failed_replacements.append({current_username: new_username})
        return Response(
            status=status.HTTP_200_OK,
            data={
                "successful_replacements": successful_replacements,
                "failed_replacements": failed_replacements
            }
        )

    def _load_models(self, models_with_fields):
        """ Takes tuples that contain a model path and returns the list with a loaded version of the model """
        try:
            replacement_locations = [(apps.get_model(model), column) for (model, column) in models_with_fields]
        except LookupError:
            log.exception("Unable to load models for username replacement")
            raise
        return replacement_locations

    def _has_valid_schema(self, post_data):
        """ Verifies the data is a list of objects with a single key:value pair """
        if not isinstance(post_data, list):
            return False
        for obj in post_data:
            if not (isinstance(obj, dict) and len(obj) == 1):
                return False
        return True

    def _generate_unique_username(self, desired_username, suffix_length=4):
        """ Accepts a username and returns a unique username if the requested is taken """
        User = apps.get_model('auth.user')
        new_username = desired_username
        # Keep checking usernames in case desired_username + random suffix is already taken
        while True:
            if User.objects.filter(username=new_username).exists():
                unique_suffix = uuid.uuid4().hex[:suffix_length]
                new_username = desired_username + unique_suffix
            else:
                break
        return new_username

    def _replace_username_for_all_models(self, current_username, new_username, replacement_locations):
        """
        Replaces current_username with new_username for all (model, column) pairs in replacement locations.
        Returns if it was successful or not. Will return successful even if no matching

        TODO: Determine if logs of username are a PII issue.
        """
        try:
            with transaction.atomic():
                num_rows_changed = 0
                for (model, column) in replacement_locations:
                    num_rows_changed += model.objects.filter(
                        **{column: current_username}
                    ).update(
                        **{column: new_username}
                    )
        except Exception as exc:
            log.exception("Unable to change username from {current} to {new}. Reason: {error}".format(
                current=current_username,
                new=new_username,
                error=exc
            ))
            return False
        if num_rows_changed == 0:
            log.warning("Unable to change username from {current} to {new} because {current} doesn't exist.".format(
                current=current_username,
                new=new_username,
            ))
            return False

        log.info("Successfully changed username from {current} to {new}.".format(
            current=current_username,
            new=new_username,
        ))
        return True

