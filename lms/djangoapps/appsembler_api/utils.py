import re

from random import randint

from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from student.forms import PasswordResetFormNoActive


def auto_generate_username(email):
    """
    This functions generates a valid username based on the email, also checks if
    the username exists and adds a random 3 digit int at the end to warranty
    uniqueness.
    """
    try:
        validate_email(email)
    except ValidationError:
        raise ValueError("Email is a invalid format")

    username = ''.join(e for e in email.split('@')[0] if e.isalnum())

    while check_account_exists(username=username):
        username = ''.join(e for e in email.split('@')[0] if e.isalnum()) + str(randint(100, 999))

    return username


def send_activation_email(request):
    form = PasswordResetFormNoActive(request.data)
    if form.is_valid():
        form.save(
            use_https=request.is_secure(),
            from_email=configuration_helpers.get_value(
                'email_from_address', settings.DEFAULT_FROM_EMAIL),
            request=request,
            subject_template_name='appsembler_api/set_password_subject.txt',
            email_template_name='appsembler_api/set_password_email.html')
        return True
    else:
        return False
