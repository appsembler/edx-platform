"""

"""
from django.conf import settings
from django.db.models import Subquery

from oauth2_provider.models import get_application_model, RefreshToken

from .models import TrustedApplication


def destroy_oauth_tokens(user):
    """
    Destroys OAuth access and refresh tokens for the given user

    All OAuth access and refresh tokens should be destroyed unless the setting,
    'KEEP_TRUSTED_CONFIDENTIAL_CLIENT_TOKENS' is `True`. If it is `True` then
    trusted application tokens should be preserved. These are tracked in the
    `openedx.core.djangoapps.appsembler.auth.models.TrustedApplication` model
    """
    dot_refresh_query = RefreshToken.objects.filter(user=user.id)

    if settings.FEATURES.get('KEEP_TRUSTED_CONFIDENTIAL_CLIENT_TOKENS', False):
        # Appsembler: Avoid deleting the trusted confidential applications such
        # as the Appsembler Management Console
        trusted_applications = get_application_model().objects.filter(
            client_type=Application.CLIENT_CONFIDENTIAL,
            pk__in=Subquery(TrustedApplication.objects.all().values('id')),
        )
        # We could just merge the `trusted_application` into the following,
        # but keeping them apart makes it a bit easier for future debugging
        dot_refresh_query = dot_refresh_query.exclude(
            application__in=trusted_applications)

    # The following revokes each token found. The revoke() call deletes the
    # related access token and marks the refresh token as revoked and marked for
    # deletion the next time oauth2_provider.models.clear_expired() is called
    [refresh_token.revoke() for refresh_token in dot_refresh_query]
