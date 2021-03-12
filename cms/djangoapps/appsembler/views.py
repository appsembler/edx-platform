"""


"""

from django.db import transaction
from django.http import HttpResponseRedirect
from django.views.decorators.clickjacking import xframe_options_deny
from django.views.decorators.csrf import ensure_csrf_cookie

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.urls import reverse

from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.djangoapps.user_authn.views.login import (
    _get_user_by_email
)
from edxmako.shortcuts import render_to_response

# This would be a reason to use JavaScript instead of a plain HTML login form
# from openedx.core.djangoapps.user_authn.cookies import refresh_jwt_cookies, set_logged_in_cookies


def ssl_get_cert_from_request(request):
    """
    Extract user information from certificate, if it exists, returning (user, email, fullname).
    Else return None.
    """
    certkey = "SSL_CLIENT_S_DN"  # specify the request.META field to use

    cert = request.META.get(certkey, '')
    if not cert:
        cert = request.META.get('HTTP_' + certkey, '')
    if not cert:
        try:
            # try the direct apache2 SSL key
            cert = request._req.subprocess_env.get(certkey, '')  # pylint: disable=protected-access
        except Exception:  # pylint: disable=broad-except
            return ''

    return cert


def ssl_login_shortcut(func):
    """
    Python function decorator for login procedures, to allow direct login
    based on existing ExternalAuth record and MIT ssl certificate.
    """

    @transaction.non_atomic_requests
    def wrapped(*args, **kwargs):
        """
        This manages the function wrapping, by determining whether to inject
        the _external signup or just continuing to the internal function
        call.
        """

        if not settings.FEATURES.get('AUTH_USE_CERTIFICATES'):
            return func(*args, **kwargs)
        request = args[0]

        if request.user and request.user.is_authenticated:  # don't re-authenticate
            return func(*args, **kwargs)

        cert = ssl_get_cert_from_request(request)
        if not cert:        # no certificate information - show normal login window
            return func(*args, **kwargs)

        def retfun():
            """Wrap function again for call by _external_login_or_signup"""
            return func(*args, **kwargs)

        (_user, email, fullname) = _ssl_dn_extract_info(cert)
        return _external_login_or_signup(
            request,
            external_id=email,
            external_domain="ssl:MIT",
            credentials=cert,
            email=email,
            fullname=fullname,
            retfun=retfun
        )
    return wrapped


@ssl_login_shortcut
# @ensure_csrf_cookie
@xframe_options_deny
def login_page(request):
    """
    Display the login form.
    """
    # csrf_token = csrf(request)['csrf_token']
    csrf_token = ''
    if (settings.FEATURES.get('AUTH_USE_CERTIFICATES') and
            ssl_get_cert_from_request(request)):
        # SSL login doesn't require a login view, so redirect
        # to course now that the user is authenticated via
        # the decorator.
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        else:
            return redirect('/course/')
    if settings.FEATURES.get('AUTH_USE_CAS'):
        # If CAS is enabled, redirect auth handling to there
        return redirect(reverse('cas-login'))

    return render_to_response(
        'appsembler_login.html',
        {
            'csrf': csrf_token,
            'forgot_password_link': "//{base}/login#forgot-password-modal".format(base=settings.LMS_BASE),
            'platform_name': configuration_helpers.get_value('platform_name', settings.PLATFORM_NAME),
        }
    )


@ensure_csrf_cookie
def do_login(request):
    """
    Temp name, rename: login_user or something
    """

    print('JLB--Testy')
    print(request.POST)
    user = _get_user_by_email(request)
    password = request.POST['password']
    if not user or not password:
        # We need to include a failed password
        return render(request, 'login_fail.html')
    user = authenticate(request, username=user.username, password=password)
    if not user:
        return HttpResponse('Whoops! no user for loing attempt')
        return render(request, 'login_fail.html')
    if user is not None:
        login(request, user)
        # Redirect to a success page.
        # print('user logged in. home = {}'.format(reverse('home')))

        # urllib.parse.join has this annoying habit of returning only the
        # revers when called like this, and not the host
        # url = urljoin(request.get_host(), reverse('home'))
        # url = request.get_host() + reverse('home')

        return redirect(reverse('home'))

        # redirect_url=''
        # response = JsonResponse({
        #     'success': True,
        #     'redirect_url': redirect_url,
        # })

        # Ensure that the external marketing site can
        # detect that the user is logged in.

        # Might need to call this, or at least some form of it
        #return set_logged_in_cookies(request, response, possibly_authenticated_user)

    else:
        # Return an 'invalid login' error message.
        return HttpResponse('test login failed')



def do_logout(request):
    """Basic logout to get Studio login/logout working
    """
    logout(request)

    # TODO: Add redirect setting to choose to go to studio home or default
    # to "https://appsembler.com/tahoe/"
    if settings.LOGOUT_REDIRECT_URL:
        return redirect(settings.LOGOUT_REDIRECT_URL)
    else:
        return redirect(reverse('home'))
