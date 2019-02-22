"""
Permissions classes for User accounts API views.
"""
from __future__ import unicode_literals

from rest_framework import permissions

USERNAME_REPLACEMENT_GROUP = "username_replacement_admin"

class CanDeactivateUser(permissions.BasePermission):
    """
    Grants access to AccountDeactivationView if the requesting user is a superuser
    or has the explicit permission to deactivate a User account.
    """
    def has_permission(self, request, view):
        return request.user.has_perm('student.can_deactivate_users')

class CanReplaceUsername(permissions.BasePermission):
    """
    Grants access to the Username Replacement API for anyone in the group,
    including the service user.
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name=USERNAME_REPLACEMENT_GROUP).exists()
