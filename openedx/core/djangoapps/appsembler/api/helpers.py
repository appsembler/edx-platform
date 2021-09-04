from opaque_keys.edx.keys import CourseKey

from openedx.core.djangoapps.appsembler.api.v1.mixins import TahoeAuthMixin
from django.core.validators import ValidationError


def as_course_key(course_id):
    '''Returns course id as a CourseKey instance

    Convenience method to return the paramater unchanged if it is of type
    ``CourseKey`` or attempts to convert to ``CourseKey`` if of type str or
    unicode.

    Raises TypeError if an unsupported type is provided
    '''
    if isinstance(course_id, CourseKey):
        return course_id
    elif isinstance(course_id, str):
        return CourseKey.from_string(course_id)
    else:
        raise TypeError('Unable to convert course id with type "{}"'.format(
            type(course_id)))


def normalize_bool_param(unnormalized):
    """
    Allow strings of any case (upper/lower) to be used by the API caller.
    For example "False", "false", "TRUE"
    """
    normalized = str(unnormalized).lower()
    if normalized not in ['false', 'true']:
        raise ValidationError('invalid value "{}" for boolean type'.format(unnormalized))
    return True if normalized == 'true' else False


def skip_registration_email_for_registration_api(request):
    """
    Helper to check if the Registration API caller has requested email to be skipped.

    This function is a helper for `_skip_activation_email` to allow customers to _not_ send
    activation emails when using the Tahoe Registration APIs.
    """
    skip_email = False
    if request and request.method == 'POST':
        # TODO: RED-1647 add TahoeAuthMixin permission checks
        should_send = request.POST.get('send_activation_email', True)
        skip_email = not normalize_bool_param(should_send)

    return skip_email
