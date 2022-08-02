import logging
from rest_framework import permissions
from organizations.models import Organization
from tahoe_sites.api import (
    get_organization_for_user,
    get_site_by_organization,
    is_active_admin_on_organization,
)

log = logging.Logger(__name__)


class AMCAdminPermission(permissions.BasePermission):
    """
    Allow making changes only if you're designated as an admin in AMC.
    """

    # TODO: RED-2845 Remove this class when AMC is removed.
    def has_permission(self, request, view):
        try:
            caller_filtered_site_id = view.get_filtered_site_id()
        except AttributeError:
            # Alert us that we're using this permission class in the wrong way
            log.exception('AMCAdminPermission failed: ({view_class}::get_filtered_site_id) method is missing ()'.format(
                view_class=type(view).__name__,
            ))
            return False

        user = request.user
        if user.is_superuser:
            return True

        try:
            organization = get_organization_for_user(user=user)
        except Organization.DoesNotExist:
            return False

        if not is_active_admin_on_organization(user=user, organization=organization):
            return False

        site = get_site_by_organization(organization=organization)
        if caller_filtered_site_id and caller_filtered_site_id != site.id:
            return False

        return True
