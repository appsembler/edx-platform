from rest_framework.permissions import BasePermission
from opaque_keys.edx.keys import CourseKey
from django.contrib.sites.shortcuts import get_current_site
from organizations.models import Organization, OrganizationCourse, UserOrganizationMapping

# def is_site_admin_user(request):

#     current_site = django.contrib.sites.shortcuts.get_current_site(request)

#     # get orgs for the site
#     orgs = Organization.objects.filter(sites__in=[current_site])

#     # Should just be mappings for organizations in this site
#     # If just one organization in a site, then the queryset returned
#     # should contain just one element

#     uom_qs = UserOrganizationMapping.objects.filter(
#         organization__in=orgs,
#         user=request.user)

#     # Since Tahoe does just one org, we're going to cheat and just look
#     # for the first element
#     if uom_qs:
#         return uom_qs[0].is_amc_admin and uom_qs[0].is_active
#     else:
#         return False




class IsAMCAdmin(BasePermission):
    def has_permission(self, request, view):
        
        print('#'*99)
        print('#'*99)
        print('#'*99)
        print('#'*99)
        
        #course_key = CourseKey.from_string(view.kwargs.get('course_id'))

        #return request.user.is_staff

        current_site = get_current_site(request)
        # get orgs for the site
        orgs = Organization.objects.filter(sites__in=[current_site])

        uom_qs = UserOrganizationMapping.objects.filter(
            organization__in=orgs,
            user=request.user)

        if not uom_qs or not uom_qs[0].is_amc_admin or not uom_qs[0].is_active:
            return False

        organization_course = OrganizationCourse.objects.filter(course_id=view.kwargs.get('course_id')).first()

        return organization_course.organization.id == uom_qs[0].organization.id