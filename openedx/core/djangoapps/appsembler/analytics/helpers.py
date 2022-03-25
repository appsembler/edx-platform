"""
Helpers for the Appsembler Analytics app.
"""

from tahoe_sites.api import deprecated_get_admin_users_queryset_by_email


def should_show_hubspot(user):
    if not user or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    if user.is_superuser or user.is_staff:
        return False

    is_active_admin = user.id in list(deprecated_get_admin_users_queryset_by_email(email=user.email))
    if not is_active_admin:
        return False

    return True
