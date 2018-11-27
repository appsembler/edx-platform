"""

"""

import random
import string

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from student.views import create_account_with_params

from ..permissions import IsSiteAdminUser


def create_password():
    """
    Copied over from appsembler_api `CreateUserAccountWithoutPasswordView`
    """
    return ''.join(
        random.choice(
            string.ascii_uppercase + string.ascii_lowercase + string.digits)
        for _ in range(32))


#
# Mixins for API views
#


class CommonAuthMixin(object):
    '''Provides a common authorization base for the Figures API views

    '''
    authentication_classes = (
        TokenAuthentication,
    )
    permission_classes = (
        IsAuthenticated,
        IsSiteAdminUser,
    )


class RegistrationViewSet(CommonAuthMixin, viewsets.ViewSet):

    http_method_names = ['post', 'head']

    def create(self, request):
        """Creates a new user account for the site that calls this view

        To use, perform a token authenticated POST to the URL::

            /tahoe/api/v1/registrations/

        Required arguments (JSON data):
            "username"
            "email"
            "password"
            "name"

        Optional arguments:
            "send_activation_email"

        Returns:
            HttpResponse: 200 on success, {"user_id ": 9}
            HttpResponse: 400 if the request is not valid.
            HttpResponse: 409 if an account with the given username or email
                address already exists

        The code here is adapted from the LMS ``appsembler_api`` bulk registration
        code. See the ``appsembler/ginkgo/master`` branch
        """
        data = request.data

        # set the honor_code and honor_code like checked,
        # so we can use the already defined methods for creating an user
        data['honor_code'] = "True"
        data['terms_of_service'] = "True"

        if 'send_activation_email' in data and data['send_activation_email'] == "False":
            data['send_activation_email'] = False
        else:
            data['send_activation_email'] = True

        email = request.data.get('email')
        username = request.data.get('username')

        # Handle duplicate email/username
        conflicts = check_account_exists(email=email, username=username)
        if conflicts:
            errors = {"user_message": "User already exists"}
            return Response(errors, status=409)

        if 'password' not in data:
            data['password'] = create_password()
        try:
            user = create_account_with_params(request, data)
            # set the user as active
            user.is_active = True
            user.save()
            user_id = user.id
        except ValidationError as err:
            print('ValidationError. err={}'.format(err))
            # Should only get non-field errors from this function
            assert NON_FIELD_ERRORS not in err.message_dict
            # Only return first error for each field

            # TODO: Let's give a clue as to which are the error causing fields
            errors = {
                "user_message": "Invalid parameters on user creation"
            }
            return Response(errors, status=400)
        return Response({'user_id ': user_id}, status=200)
