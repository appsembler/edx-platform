import json
import logging
import string
import random

from dateutil import parser

from django.http import Http404
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from util.bad_request_rate_limiter import BadRequestRateLimiter
from util.disable_rate_limit import can_disable_rate_limit

from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from openedx.core.lib.api.authentication import (
    OAuth2AuthenticationAllowInactiveUser,
    AuthenticationFailed,
)
from openedx.core.lib.api.permissions import (
    IsStaffOrOwner, ApiKeyHeaderPermissionIsAuthenticated
)

from student.views import create_account_with_params
from student.models import CourseEnrollment, EnrollmentClosedError, \
    CourseFullError, AlreadyEnrolledError
from student.roles import (
    REGISTERED_ACCESS_ROLES,
    CourseRole,
    CourseInstructorRole,
)

from course_modes.models import CourseMode
from courseware.access import has_access
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
            HttpResponse: 200 on success, {"user_id ": 9, "success": true }
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

        response = Response({'user_id ': user_id }, status=200)
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
            print account_settings
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
            course_id= course_id.replace(' ', '+')
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


class CourseRolesView(APIView):
    authentication_classes = (OAuth2AuthenticationAllowInactiveUser,)
    permission_classes = (IsAdminUser,)
    # lookup_field = 'course_id'

    # TODO: Consider reusing some methods from `CourseViewMixin` for
    #       this class instead of rolling my own.

    # TODO: Make sure write operations are guarded i.e. transactional

    @property
    def course_roles(self):
        return [
            role_class for role_class in REGISTERED_ACCESS_ROLES.values()
            if issubclass(role_class, CourseRole)
        ]

    def get_course(self):
        try:
            course_id = self.kwargs.get('course_id')
            course_key = CourseKey.from_string(course_id)
            course = get_course_by_id(course_key)
            return course
        except ValueError:
            raise Http404

    def get(self, request, *args, **kwargs):
        course = self.get_course()

        course_users = {}
        for role_class in self.course_roles:
            role = role_class(course.id)
            # TODO: Use a serializer!

            course_users[role.ROLE] = [{
                'id': user.id,
                'email': user.email,
                'username': user.username,
                # TODO: Add a full name?
            } for user in role.users_with_role()]

        return Response({
            'course': {
                'id': unicode(course.id),
                'name': course.display_name,
            },
            'roles': course_users,
        }, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        course = self.get_course()
        roles = request.data.get('roles')
        if not roles or not type(roles) == dict:
            return Response({
                'detail': 'Invalid or missing `roles` parameter.',
            }, status=status.HTTP_400_BAD_REQUEST)

        # TODO: Deduplicate
        for role_class in self.course_roles:
            user_queries = roles.get(role_class.ROLE, [])
            if not user_queries:
                continue

            users = []
            for user_query in user_queries:
                try:
                    user = User.objects.get(Q(username=user_query) | Q(email=user_query))
                except User.DoesNotExist:
                    # TODO: Consider verbosely ignore those users
                    return Response({
                        'detail': u'User `{}` was not found'.format(user_query),
                    }, status=status.HTTP_404_NOT_FOUND)

                users.append(user)

            role_class(course.id).add_users(*users)

        return Response({
            'detail': 'Course roles has been updated.'
        }, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        # TODO: Refactor copypasta from the PUT method
        course = self.get_course()
        roles = json.loads(request.GET.get('roles', '{}'))

        for role_class in self.course_roles:
            user_queries = roles.get(role_class.ROLE, [])
            if not user_queries:
                continue

            users = []
            for user_query in user_queries:
                try:
                    user = User.objects.get(Q(username=user_query) | Q(email=user_query))
                    users.append(user)
                except User.DoesNotExist:
                    # Delete is idempotent, so no worries about missing users
                    pass

            role_class(course.id).remove_users(*users)

        return Response({
            'detail': 'Course roles has been updated.'
        }, status=status.HTTP_200_OK)
