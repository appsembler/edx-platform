"""
Default filter backend for full DRF API.

Set via  REST_FRAMEWORK settings

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'openedx.core.djangoapps.appsembler.openedx_api.filters.AppsemblerMultiTenantFilterBackend'
    ]
}

Implement django_filters Filterset to provide a final filter by
allowed course Organization to ensure multitenant-safe API results.

..
The APIs we want to support are (draft):
see https://courses.edx.org/api-docs/

Certificates (GeneratedCertificate.course_id__org)
Cohorts (CourseUserGroup.course_id -> no FK to courseoverview)
Completion (BlockCompletion.course_id__org)
? Course Experience ()
? Course Home ()
Courses (CourseOverview.org)        
Courseware (CourseOverview.org)
Discussion (not sure how to handle... discussions aren't Django objs, just gets course via lms.djangoapps.courseware.courses.get_course_with_access)
Enrollment (CourseEnrollment.course__org)
Grades:  not sure yet how these are serialized... 
...or if they use PersistentGrades.         
User (User.organizations__contains)
...

"""

from django.contrib.auth.models import User

from django_filters import rest_framework as filters
from django_filters import rest_framework  

from completion.models import BlockCompletion
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from lms.djangoapps.certificates.models import GeneratedCertificate
from organizations.models import Organization
from student.models import CourseEnrollment


COURSE_PREFIX = 'course-v1:'


# TODO: Need to figure out how to limit this FilterBackend (or make essentially no-op) for some parts of API 


class AppsemblerMultiTenantFilterBackend(filters.DjangoFilterBackend):
    
    filterset_base = AllowedCourseOrgFilterSet


class AllowedCourseOrgFilterSet(filters.FilterSet):
    """Filter by allowed organization, with dynamic queryset filter. 
    """
    MODEL_COURSE_ORG_LOOKUPS = {
      User: 'organizations__contains',
      CourseEnrollment: 'course__org',
      CourseOverview: 'org',
      CourseUserGroup: 'course_id__startswith',
      GeneratedCertificate: 'course_id__startswith',
      BlockCompletion: 'context_key__startswith',
    }
    
    # have no ForeignKey to CourseOverview or other path to Organization,
    # just an OpaqueKeyField subclass so we have to do a string comparison
    OPAQUE_KEY_FIELD_LOOKUP_MODELS = (
      BlockCompletion,
      CourseUserGroup, 
      GeneratedCertificate, 
    )
    
    # org field is just a string of the name of the org.
    STRING_ORG_NAME_LOOKUP_MODELS = (
      CourseEnrollment,
      CourseOverview,
    )
    
    # TODO: Allow a superuser to bypass filter

    allowed_org = filters.BooleanFilter(method="filter_allowed_org")
    
    def filter_allowed_org(self, queryset, name, value):
        import pdb; pdb.set_trace()
        requesting_user = self.request.user
        
        try:
          user_allowed_org = self.request.user.organizations.first()
        except Organization.DoesNotExist:
            raise  # TODO: do something else
        
        try:
            lookup = MODEL_COURSE_ORG_LOOKUPS[self.queryset.model]
        except KeyError:
            raise  # TODO: do something else
                
        if model in OPAQUE_KEY_FIELD_LOOKUP_MODELS:
            return queryset.filter(**{lookup: "{}{}+".format(COURSE_PREFIX, user_allowed_org)})
        elif model in STRING_ORG_NAME_LOOKUP_MODELS:
            return queryset.filter(**{lookup: user_allowed_org.short_name})        
        else:
            return queryset.filter(**{lookup: user_allowed_org})
          
    # don't declare an explicit model via Meta
