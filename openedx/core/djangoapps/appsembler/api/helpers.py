import beeline

from opaque_keys.edx.keys import CourseKey

from openedx.core.djangoapps.appsembler.api.v1.mixins import TahoeAuthMixin


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


@beeline.traced(name='register.skip_registration_email_for_registration_api')
def skip_registration_email_for_registration_api(request):
    """
    Helper to check if the Registration API caller has requested email to be skipped.

    This function is a helper for `_skip_activation_email` to allow customers to _not_ send
    activation emails when using the Tahoe Registration APIs.
    """
    skip_email = False
    if request and request.method == 'POST':
        # TODO: RED-1647 add TahoeAuthMixin permission checks
        user_email = request.POST.get('email', '')
        skip_email = not request.POST.get('send_activation_email', True)
        beeline.add_context_field('skip_registration_email_for_registration_api__user_email', user_email)
    beeline.add_context_field('skip_registration_email_for_registration_api__skip_email', skip_email)

    return skip_email
