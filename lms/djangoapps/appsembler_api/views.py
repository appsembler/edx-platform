import json
import logging
import string
import random

import search
from dateutil import parser

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.http import Http404
from django.db.models import Q
from django.core.validators import validate_email
from rest_framework.generics import ListAPIView

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from util.bad_request_rate_limiter import BadRequestRateLimiter
from util.disable_rate_limit import can_disable_rate_limit

from lms.djangoapps.course_api.api import list_courses
from lms.djangoapps.course_api.serializers import CourseSerializer
from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from openedx.core.lib.api.authentication import (
    OAuth2AuthenticationAllowInactiveUser,
)
from openedx.core.lib.api.paginators import NamespacedPageNumberPagination
from openedx.core.lib.api.permissions import (
    IsStaffOrOwner, ApiKeyHeaderPermissionIsAuthenticated
)

from student.forms import get_registration_extension_form
from student.views import create_account_with_params
from student.models import CourseEnrollment, EnrollmentClosedError, \
    CourseFullError, AlreadyEnrolledError, UserProfile

from course_modes.models import CourseMode
from courseware.courses import get_course_by_id
from enrollment.views import EnrollmentCrossDomainSessionAuth, \
    EnrollmentUserThrottle, ApiKeyPermissionMixIn

from instructor.views.api import save_registration_code, \
    students_update_enrollment, require_level

from shoppingcart.exceptions import RedemptionCodeError
from shoppingcart.models import (
    RegistrationCodeRedemption, CourseRegistrationCode
)
from shoppingcart.views import get_reg_code_validity

from opaque_keys.edx.keys import CourseKey
from certificates.models import GeneratedCertificate

from openedx.core.lib.api.view_utils import view_auth_classes, DeveloperErrorViewMixin
from .forms import CourseListGetAndSearchForm
from .serializers import BulkEnrollmentSerializer
from .utils import auto_generate_username, send_activation_email

log = logging.getLogger(__name__)


class CreateUserAccountView(APIView):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser,
    permission_classes = IsStaffOrOwner,

    def post(self, request):
        """
        Creates a new user account
        URL: /api/ps_user_api/v1/accounts/create
        Arguments:
            request (HttpRequest)
            JSON (application/json)
            {
                "username": "staff4",
                "password": "edx",
                "email": "staff4@example.com",
                "name": "stafftest"
            }
        Returns:
            HttpResponse: 200 on success, {"user_id": 9, "success": true }
            HttpResponse: 400 if the request is not valid.
            HttpResponse: 409 if an account with the given username or email
                address already exists
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

        try:
            user = create_account_with_params(request, data)
            # set the user as active
            user.is_active = True
            user.save()
            user_id = user.id
        except ValidationError as err:
            # Should only get non-field errors from this function
            assert NON_FIELD_ERRORS not in err.message_dict
            # Only return first error for each field
            errors = {"user_message": "Wrong parameters on user creation"}
            return Response(errors, status=400)

        response = Response({'user_id ': user_id}, status=200)
        return response


class CreateUserAccountWithoutPasswordView(APIView):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser,
    permission_classes = IsStaffOrOwner,

    def post(self, request):
        """

        """
        data = request.data

        # set the honor_code and honor_code like checked,
        # so we can use the already defined methods for creating an user
        data['honor_code'] = "True"
        data['terms_of_service'] = "True"

        email = request.data.get('email')

        # Handle duplicate email/username
        conflicts = check_account_exists(email=email)
        if conflicts:
            errors = {"user_message": "User already exists"}
            return Response(errors, status=409)

        try:
            username = auto_generate_username(email)
            password = ''.join(random.choice(
                string.ascii_uppercase + string.ascii_lowercase + string.digits)
                for _ in range(32))

            data['username'] = username
            data['password'] = password
            data['send_activation_email'] = False

            user = create_account_with_params(request, data)
            # set the user as inactive
            user.is_active = False
            user.save()
            user_id = user.id
            send_activation_email(request)
        except ValidationError as err:
            # Should only get non-field errors from this function
            assert NON_FIELD_ERRORS not in err.message_dict
            # Only return first error for each field
            errors = {"user_message": "Wrong parameters on user creation"}
            return Response(errors, status=400)
        except ValueError as err:
            errors = {"user_message": "Wrong email format"}
            return Response(errors, status=400)

        response = Response({'user_id': user_id, 'username': username}, status=200)
        return response


class UserAccountConnect(APIView):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser,
    permission_classes = IsStaffOrOwner,

    def post(self, request):
        """
        Connects an existing Open edX user account to one in an external system
        changing the user password, email or full name.

        URL: /appsembler_api/v0/accounts/connect
        Arguments:
            request (HttpRequest)
            JSON (application/json)
            {
                "username": "staff4@example.com", # mandatory, the lookup param
                "password": "edx",
                "email": staff@example.com,
                "name": "Staff edX"
            }
        Returns:
            HttpResponse: 200 on success, {"user_id ": 60}
            HttpResponse: 404 if the doesn't exists
            HttpResponse: 400 Incorrect parameters, basically if the password
                          is empty.
        """
        data = request.data

        username = data.get('username', '')
        new_email = data.get('email', '')
        new_password = data.get('password', '')
        new_name = data.get('name', '')

        try:
            user = User.objects.get(username=username)

            if new_password.strip() != "":
                user.set_password(new_password)

            if new_email.strip() != "" and new_email != user.email:
                try:
                    validate_email(new_email)

                    if check_account_exists(email=new_email):
                        errors = {
                            "user_message": "The email %s is in use by another user" % (
                                new_email)}
                        return Response(errors, status=409)

                    user.email = new_email
                except ValidationError:
                    errors = {"user_message": "Invalid email format"}
                    return Response(errors, status=409)

            if new_name.strip() != "":
                user.profile.name = new_name
                user.profile.save()

            user.save()

        except User.DoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND
            )
        except ValidationError:
            errors = {"user_message": "Wrong parameters on user connection"}
            return Response(errors, status=400)

        response = Response({'user_id': user.id}, status=200)
        return response


class UpdateUserAccount(APIView):
    """ HTTP endpoint for updating and user account """

    authentication_classes = OAuth2AuthenticationAllowInactiveUser,
    permission_classes = IsStaffOrOwner,

    def post(self, request):
        """
        This endpoint allows to change user attributes including email, profile
        attributes and extended profile fields. Receives one mandatory param
        user_lookup that can be an email or username to lookup the user to
        update and the rest of parameters are option. Any attribute to update
        must be sent in key:val JSON format.

        URL: /appsembler_api/v0/accounts/update_user
        Arguments:
            request (HttpRequest)
            JSON (application/json)
            {
                "user_lookup": email or username to lookup the user to update,
                # mandatory ex: "staff4@example.com" or "staff4"

                "email": "staff@example.com",
                "bio": "this is my bio",
                "country": "BR"
            }
        Returns:
            HttpResponse: 200 on success, {"success ": "list of updated params"}
            HttpResponse: 404 if the doesn't exists
            HttpResponse: 400 Incorrect parameters, basically if username or
            email parameter is not sent
        """
        data = request.data

        if data['user_lookup'].strip() == "":
            errors = {"lookup_error": "No user lookup has been provided"}
            return Response(errors, status=400)

        user = User.objects.filter(
            Q(username=data['user_lookup']) | Q(email=data['user_lookup'])
        )

        if user:
            user = user[0]
        else:
            errors = {
                "user_not_found": "The user for the Given username or email doesn't exists"
            }
            return Response(errors, status=404)

        updated_fields = {}

        # update email
        if 'email' in data and data['email'] != user.email:
            user_exists = check_account_exists(email=data['email'])
            if user_exists:
                errors = {"integrity_error": "the user email you're trying to set already belongs to another user"}
                return Response(errors, status=400)

            user.email = data['email']
            user.save()
            updated_fields.update({'email': data['email']})

        # update profile fields
        profile_fields = [
            "name", "level_of_education", "gender", "mailing_address", "city",
            "country", "goals", "bio", "year_of_birth", "language"
        ]

        profile_fields_to_update = {}
        for field in profile_fields:
            if field in data:
                profile_fields_to_update[field] = data[field]

        if len(profile_fields_to_update):
            UserProfile.objects.filter(user=user).update(**profile_fields_to_update)
            updated_fields.update(profile_fields_to_update)

        # If there is an exension form fields installed update them too
        custom_profile_fields_to_update = {}
        custom_form = get_registration_extension_form()

        if custom_form is not None:
            for custom_field in custom_form.fields:
                if custom_field in data:
                    custom_profile_fields_to_update[custom_field] = data[custom_field]
                    updated_fields.update(custom_profile_fields_to_update)

            if len(custom_profile_fields_to_update):
                custom_form.Meta.model.objects.filter(user=user).update(
                    **custom_profile_fields_to_update)

        return Response(
            {
                "success": "The following fields has been updated: {}".format(
                    ', '.join(
                        '{}={}'.format(f, v) for f, v in updated_fields.items())
                )
            },
            status=200)


class GetUserAccountView(APIView):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser,
    permission_classes = IsStaffOrOwner,

    def get(self, request, username):
        """
        check if a user exists based in the username

        URL: /api/ps_user_api/v1/accounts/{username}
        Args:
            username: the username you are looking for

        Returns:
            200 OK and the user id
            404 NOT_FOUND if the user doesn't exists

        """
        try:
            account_settings = User.objects.select_related('profile').get(username=username)
        except User.DoesNotExist:
            return Response(
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({'user_id': account_settings.username}, status=200)


@can_disable_rate_limit
class BulkEnrollView(APIView, ApiKeyPermissionMixIn):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser, \
        EnrollmentCrossDomainSessionAuth
    permission_classes = ApiKeyHeaderPermissionIsAuthenticated,
    throttle_classes = EnrollmentUserThrottle,

    def post(self, request):
        serializer = BulkEnrollmentSerializer(data=request.data)
        if serializer.is_valid():
            request.POST = request.data
            response_dict = {
                'auto_enroll': serializer.data.get('auto_enroll'),
                'email_students': serializer.data.get('email_students'),
                'action': serializer.data.get('action'),
                'courses': {}
            }
            for course in serializer.data.get('courses'):
                response = students_update_enrollment(
                    self.request, course_id=course
                )
                response_dict['courses'][course] = json.loads(response.content)
            return Response(data=response_dict, status=status.HTTP_200_OK)
        else:
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )


class GenerateRegistrationCodesView(APIView):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser, \
        EnrollmentCrossDomainSessionAuth
    permission_classes = IsStaffOrOwner,

    def post(self, request):
        course_id = CourseKey.from_string(request.data.get('course_id'))

        try:
            course_code_number = int(
                request.data.get('total_registration_codes')
            )
        except ValueError:
            course_code_number = int(
                float(request.data.get('total_registration_codes'))
            )

        course_mode = CourseMode.DEFAULT_MODE_SLUG

        registration_codes = []
        for __ in range(course_code_number):
            generated_registration_code = save_registration_code(
                request.user, course_id, course_mode, order=None,
            )
            registration_codes.append(generated_registration_code.code)

        return Response(
            data={
                'codes': registration_codes,
                'course_id': request.data.get('course_id'),
                'course_url': reverse(
                    'about_course',
                    kwargs={'course_id': request.data.get('course_id')}
                )
            }
        )


class EnrollUserWithEnrollmentCodeView(APIView):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser, \
        EnrollmentCrossDomainSessionAuth
    permission_classes = IsStaffOrOwner,

    def post(self, request):
        enrollment_code = request.data.get('enrollment_code')
        limiter = BadRequestRateLimiter()
        error_reason = ""
        try:
            user = User.objects.get(email=request.data.get('email'))
            user_is_valid = True
        except User.DoesNotExist:
            user_is_valid = False
            error_reason = "User not found"
        try:
            reg_code_is_valid, reg_code_already_redeemed, course_registration = get_reg_code_validity(
                enrollment_code,
                request,
                limiter
            )
        except Http404:
            reg_code_is_valid = False
            reg_code_already_redeemed = False
            error_reason = "Enrollment code not found"
        if user_is_valid and reg_code_is_valid:
            course = get_course_by_id(course_registration.course_id, depth=0)
            redemption = RegistrationCodeRedemption.create_invoice_generated_registration_redemption(
                course_registration,
                user)
            try:
                kwargs = {}
                if course_registration.mode_slug is not None:
                    if CourseMode.mode_for_course(course.id, course_registration.mode_slug):
                        kwargs['mode'] = course_registration.mode_slug
                    else:
                        raise RedemptionCodeError()
                redemption.course_enrollment = CourseEnrollment.enroll(user, course.id, **kwargs)
                redemption.save()
                return Response(data={
                    'success': True,
                })
            except RedemptionCodeError:
                error_reason = "Enrollment code error"
            except EnrollmentClosedError:
                error_reason = "Enrollment closed"
            except CourseFullError:
                error_reason = "Course full"
            except AlreadyEnrolledError:
                error_reason = "Already enrolled"
        return Response(
            data={
                'success': False,
                'reason': error_reason,
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class EnrollmentCodeStatusView(APIView):
    """
    This endpoint controls the status of the enrollment codes. Receives two parameters: enrollment_code and the action
    cancel or restore.
    cancel: If the code was user for enroll an user, the user is unenrolled and the code becomes unavailable.
    restore: If the code was user for enroll an user, the user is unenrolled and the code becomes available for use it
    again.
    """
    authentication_classes = OAuth2AuthenticationAllowInactiveUser, EnrollmentCrossDomainSessionAuth
    permission_classes = IsStaffOrOwner,

    def post(self, request):
        code = request.data.get('enrollment_code')
        action = request.data.get('action')
        try:
            registration_code = CourseRegistrationCode.objects.get(code=code)
        except CourseRegistrationCode.DoesNotExist:
            return Response(
                data={
                    'reason': 'The enrollment code ({code}) was not found'.format(code=code),
                    'success': False},
                status=400
            )
        # check if the code was in use (redeemed)
        redemption = RegistrationCodeRedemption.get_registration_code_redemption(registration_code.code,
                                                                                 registration_code.course_id)
        if action == 'cancel':
            if redemption:
                # if was redeemed, unenroll the user from the course and delete the redemption object.
                CourseEnrollment.unenroll(redemption.course_enrollment.user, registration_code.course_id)
                redemption.delete()
            # make the enrollment code unavailable
            registration_code.is_valid = False
            registration_code.save()

        if action == 'restore':
            if redemption:
                # if was redeemed, unenroll the user from the course and delete the redemption object.
                CourseEnrollment.unenroll(redemption.course_enrollment.user, registration_code.course_id)
                redemption.delete()
            # make the enrollment code available
            registration_code.is_valid = True
            registration_code.save()
        return Response(data={'success': True})


class GetBatchUserDataView(APIView):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser,
    permission_classes = IsStaffOrOwner,

    def get(self, request):
        """
            /appsembler_api/v0/analytics/accounts/batch[?time-parameter]

            time-parameter is an optional query parameter of:
                ?updated_min=yyyy-mm-ddThh:mm:ss
                ?updated_max=yyyy-mm-ddThh:mm:ss
                ?updated_min=yyyy-mm-ddThh:mm:ss&updated_max=yyyy-mm-ddThh:mm:ss

        """
        updated_min = request.GET.get('updated_min', '')
        updated_max = request.GET.get('updated_max', '')

        users = User.objects.all()
        if updated_min:
            min_date = parser.parse(updated_min)
            users = users.filter(date_joined__gt=min_date)

        if updated_max:
            max_date = parser.parse(updated_max)
            users = users.filter(date_joined__lt=max_date)

        user_list = []
        for user in users:
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'date_joined': user.date_joined
            }
            user_list.append(user_data)

        return Response(user_list, status=200)


@view_auth_classes(is_authenticated=False)
class CourseListSearchView(DeveloperErrorViewMixin, ListAPIView):
    """
    **Use Cases**

        Request information on all courses visible to the specified user with search.

    **Example Requests**

        GET /appsembler_api/v0/search_courses?search_term=master

    **Response Values**

        Body comprises a list of objects as returned by `CourseDetailView`.

    **Parameters**
        search_term (optional):
            Textual search term to filter courses.

        username (optional):
            The username of the specified user whose visible courses we
            want to see. The username is not required only if the API is
            requested by an Anonymous user.

        org (optional):
            If specified, visible `CourseOverview` objects are filtered
            such that only those belonging to the organization with the
            provided org code (e.g., "HarvardX") are returned.
            Case-insensitive.

        mobile (optional):
            If specified, only visible `CourseOverview` objects that are
            designated as mobile_available are returned.


    **Returns**

        * 200 on success, with a list of course discovery objects as returned
          by `CourseDetailView`.
        * 400 if an invalid parameter was sent or the username was not provided
          for an authenticated request.
        * 403 if a user who does not have permission to masquerade as
          another user specifies a username other than their own.
        * 404 if the specified user does not exist, or the requesting user does
          not have permission to view their courses.

        Example response:

            [
              {
                "blocks_url": "/api/courses/v1/blocks/?course_id=edX%2Fexample%2F2012_Fall",
                "media": {
                  "course_image": {
                    "uri": "/c4x/edX/example/asset/just_a_test.jpg",
                    "name": "Course Image"
                  }
                },
                "description": "An example course.",
                "end": "2015-09-19T18:00:00Z",
                "enrollment_end": "2015-07-15T00:00:00Z",
                "enrollment_start": "2015-06-15T00:00:00Z",
                "course_id": "edX/example/2012_Fall",
                "name": "Example Course",
                "number": "example",
                "org": "edX",
                "start": "2015-07-17T12:00:00Z",
                "start_display": "July 17, 2015",
                "start_type": "timestamp"
              }
            ]
    """

    pagination_class = NamespacedPageNumberPagination
    serializer_class = CourseSerializer

    # Return all the results, 10K is the maximum allowed value for ElasticSearch.
    # We should use 0 after upgrading to 1.1+:
    #   - https://github.com/elastic/elasticsearch/commit/8b0a863d427b4ebcbcfb1dcd69c996c52e7ae05e
    results_size_infinity = 10000

    def get_queryset(self):
        """
        Return a list of courses visible to the user.
        """
        form = CourseListGetAndSearchForm(self.request.query_params, initial={'requesting_user': self.request.user})
        if not form.is_valid():
            raise ValidationError(form.errors)

        courses_db = list_courses(
            self.request,
            form.cleaned_data['username'],
            org=form.cleaned_data['org'],
            filter_=form.cleaned_data['filter_'],
        )

        courses_search = search.api.course_discovery_search(
            form.cleaned_data['search_term'],
            size=self.results_size_infinity,
        )

        course_search_ids = {course['data']['id']: True for course in courses_search['results']}

        return [
            course for course in courses_db
            if unicode(course.id) in course_search_ids
        ]


class GetBatchEnrollmentDataView(APIView):
    authentication_classes = OAuth2AuthenticationAllowInactiveUser,
    permission_classes = IsStaffOrOwner,

    def get(self, request):
        """
        /appsembler_api/v0/analytics/accounts/batch[?course_id=course_slug&time-parameter]

        course_slug an optional query parameter; if specified will only show enrollments
            for that particular course. The course_id need to be URL encoded, so:
                course_id=course-v1:edX+DemoX+Demo_Course
            would be encoded as:
                course_id=course-v1%3AedX%2BDemoX%2BDemo_Course
        time-parameter is an optional query parameter of:
                ?updated_min=yyyy-mm-ddThh:mm:ss
                ?updated_max=yyyy-mm-ddThh:mm:ss
                ?updated_min=yyyy-mm-ddThh:mm:ss&updated_max=yyyy-mm-ddThh:mm:ss
        """

        updated_min = request.GET.get('updated_min', '')
        updated_max = request.GET.get('updated_max', '')
        course_id = request.GET.get('course_id')
        username = request.GET.get('username')

        query_filter = {}

        if course_id:
            course_id = course_id.replace(' ', '+')
        # the replace function is because Django encodes '+' or '%2B' as spaces

        if course_id:
            course_key = CourseKey.from_string(course_id)
            query_filter['course_id'] = course_key

        if username:
            query_filter['user__username'] = username

        if updated_min:
            min_date = parser.parse(updated_min)
            query_filter['created__gt'] = min_date

        if updated_max:
            max_date = parser.parse(updated_max)
            query_filter['created__lt'] = max_date

        enrollments = CourseEnrollment.objects.filter(**query_filter)

        enrollment_list = []
        for enrollment in enrollments:
            enrollment_data = {
                'enrollment_id': enrollment.id,
                'user_id': enrollment.user.id,
                'username': enrollment.user.username,
                'course_id': str(enrollment.course_id),
                'date_enrolled': enrollment.created,
            }
            try:
                cert = GeneratedCertificate.objects.get(course_id=enrollment.course_id, user=enrollment.user)
                enrollment_data['certificate'] = {
                    'completion_date': str(cert.created_date),
                    'grade': cert.grade,
                    'url': cert.download_url,
                }
            except GeneratedCertificate.DoesNotExist:
                pass

            enrollment_list.append(enrollment_data)

        return Response(enrollment_list, status=200)
