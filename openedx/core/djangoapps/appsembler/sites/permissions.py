from rest_framework import permissions
from organizations.models import Organization
from tahoe_sites.api import get_current_organization, is_active_admin_on_organization


class AMCAdminPermission(permissions.BasePermission):
    """
    Allow making changes only if you're designated as an admin in AMC.
    """

    def has_permission(self, request, view):
        try:
            is_organization_admin = is_active_admin_on_organization(
                user=request.user, organization=get_current_organization(request=request)
            )
        except Organization.DoesNotExist:
            is_organization_admin = False
        return is_organization_admin or request.user.is_superuser
