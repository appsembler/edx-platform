
import logging

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from lms.djangoapps.instructor.enrollment import (
    get_user_email_language,
)

from lms.djangoapps.instructor.views.tools import get_student_from_identifier

from openedx.core.djangoapps.appsembler.api.sites import (
    get_site_for_course
)
from openedx.core.djangoapps.appsembler.api.v1.waffle import FIX_ENROLLMENT_RESULTS_BUG

from student.models import (
    ALLOWEDTOENROLL_TO_ENROLLED,
    ENROLLED_TO_ENROLLED,
    DEFAULT_TRANSITION_STATE,
    UNENROLLED_TO_ENROLLED,
    UNENROLLED_TO_ALLOWEDTOENROLL,
    ENROLLED_TO_UNENROLLED,
    ALLOWEDTOENROLL_TO_UNENROLLED,
    UNENROLLED_TO_UNENROLLED,
    CourseEnrollment,
    ManualEnrollmentAudit
)


log = logging.getLogger(__name__)


def enrollment_learners_context(identifiers):
    """
    Get emails (and learner language) from a list of learner identifiers.
    :param identifiers: list of usernames/emails of students.
    :return: iterator of tuples
        (
            user: User: The User object if found,
            identifier: string: The identifier as-is -- which is either a username or an email,
            email: string: Learner email by the identifier,
            language: string: Learner language,
        )
    """
    for identifier in identifiers:
        language = None
        user = None
        try:
            user = get_student_from_identifier(identifier)
        except User.DoesNotExist:
            email = identifier
        else:
            email = user.email
            language = get_user_email_language(user)

        yield user, email, identifier, language


def enroll_learners_in_course(course_id, identifiers, enroll_func, **kwargs):
    """
    This method assumes that the site has been verified to own this course

    This method is a quick hack. It copies from the existing appsembler_api
    from Ginkgo. See:
        lms/djangoapps/instructor/views/api.py:students_update_enrollment

    ## Operational notes

    If a user does not already exist then a new entry is created in
    `CourseEnrollmentAllowed`. This is default behavior, not a new addition of
    this API.


    ## Future Design and considerations
    - We want to decouple concerns
        - email notification is a seperate method or class
    """

    reason = kwargs.get('reason', u'')
    request_user = kwargs.get('request_user')
    role = kwargs.get('role')

    results = []

    enrollment_obj = None
    state_transition = DEFAULT_TRANSITION_STATE

    for user, identifier, email, language in enrollment_learners_context(identifiers):
        try:
            # Use django.core.validators.validate_email to check email address
            # validity (obviously, cannot check if email actually /exists/,
            # simply that it is plausibly valid)
            validate_email(email)  # Raises ValidationError if invalid
            before, after, enrollment_obj = enroll_func(course_id=course_id,
                                                        student_email=email,
                                                        language=language)
            before_enrollment = before.to_dict()['enrollment']
            before_user_registered = before.to_dict()['user']
            before_allowed = before.to_dict()['allowed']
            after_enrollment = after.to_dict()['enrollment']
            after_allowed = after.to_dict()['allowed']

            if before_user_registered:
                if after_enrollment:
                    if before_enrollment:
                        state_transition = ENROLLED_TO_ENROLLED
                    else:
                        if before_allowed:
                            state_transition = ALLOWEDTOENROLL_TO_ENROLLED
                        else:
                            state_transition = UNENROLLED_TO_ENROLLED
            else:
                if after_allowed:
                    state_transition = UNENROLLED_TO_ALLOWEDTOENROLL

        except ValidationError:
            # Flag this email as an error if invalid, but continue checking
            # the remaining in the list
            results.append({
                'identifier': identifier,
                'invalidIdentifier': True,
            })

        # TODO: Broad except is an anti-pattern that we should not be using:
        #       See: https://realpython.com/the-most-diabolical-python-antipattern/
        except Exception as exc:  # pylint: disable=broad-except
            # catch and log any exceptions
            # so that one error doesn't cause a 500.
            log.exception(u"Error while enrolling student")
            results.append({
                'identifier': identifier,
                'error': True,
                'error_message': str(exc),
            })
        else:
            ManualEnrollmentAudit.create_manual_enrollment_audit(
                request_user, email, state_transition, reason, enrollment_obj, role
            )
            result = {
                'identifier': identifier,
                'before': before.to_dict(),
                'after': after.to_dict(),
            }
            if FIX_ENROLLMENT_RESULTS_BUG.is_enabled():  # TODO: RED-1387 Clean up after release
                result['course'] = str(course_id)
            results.append(result)
    return results


def unenroll_learners_in_course(course_id, identifiers, unenroll_func, **kwargs):
    """
    Unenroll learners via email or username in a course.

    This function assumes that the site has been verified to own this course

    This method is a quick hack. It copies from the existing appsembler_api
    from Ginkgo. See:
        lms/djangoapps/instructor/views/api.py:students_update_enrollment

    TODO: There's some repetition between the functions {enroll,unenroll}_learners_in_course.
          The issue is that `students_update_enrollment` isn't very modular.
          We need to refactor both of our and edX's functions to avoid having
          the `appsembler/api/v1/api.py` module altogether.
    """
    reason = kwargs.get('reason', u'')
    request_user = kwargs.get('request_user')
    role = kwargs.get('role')
    results = []
    enrollment_obj = None

    for user, identifier, email, language in enrollment_learners_context(identifiers):
        try:
            validate_email(email)  # Raises ValidationError if invalid
            before, after = unenroll_func(
                course_id=course_id,
                student_email=email,
            )
            before_enrollment = before.to_dict()['enrollment']
            before_allowed = before.to_dict()['allowed']
            enrollment_obj = CourseEnrollment.get_enrollment(user, course_id) if user else None

            if before_enrollment:
                state_transition = ENROLLED_TO_UNENROLLED
            else:
                if before_allowed:
                    state_transition = ALLOWEDTOENROLL_TO_UNENROLLED
                else:
                    state_transition = UNENROLLED_TO_UNENROLLED
        except ValidationError:
            # Flag this email as an error if invalid, but continue checking
            # the remaining in the list
            results.append({
                'identifier': identifier,
                'invalidIdentifier': True,
            })

        # TODO: Broad except is an anti-pattern that we should not be using:
        #       See: https://realpython.com/the-most-diabolical-python-antipattern/
        except Exception as exc:  # pylint: disable=broad-except
            # catch and log any exceptions
            # so that one error doesn't cause a 500.
            log.exception(u"Error while unenrolling student")
            results.append({
                'identifier': identifier,
                'error': True,
                'error_message': str(exc),
            })
        else:
            ManualEnrollmentAudit.create_manual_enrollment_audit(
                request_user, email, state_transition, reason, enrollment_obj, role
            )
            result = {
                'identifier': identifier,
                'before': before.to_dict(),
                'after': after.to_dict(),
            }
            if FIX_ENROLLMENT_RESULTS_BUG.is_enabled():  # TODO: RED-1387 Clean up after release
                result['course'] = str(course_id)
            results.append(result)
    return results
