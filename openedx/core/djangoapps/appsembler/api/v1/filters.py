
import django_filters
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import (
    CourseOverview,
)

from student.models import CourseEnrollment

from openedx.core.djangoapps.appsembler.api.helpers import as_course_key


class CourseOverviewFilter(django_filters.FilterSet):
    '''Provides filtering for CourseOverview model objects

    Filters to consider adding:
        description: search/icontains
        enrollment start: date exact/lt, gt, range
        enrollment end: date exact/lt, gt, range

    Outstanding issues:

        CourseOverview.id is not yet in the filter, as filtering a
        string representation of the course id in the query params
        causes the following::

            AssertionError: <course id string repr> is not an instance of
            <class 'opaque_keys.edx.keys.CourseKey'>

    '''

    display_name = django_filters.CharFilter(lookup_expr='icontains')
    org = django_filters.CharFilter(
        name='display_org_with_default', lookup_expr='iexact')
    number = django_filters.CharFilter(
        name='display_number_with_default', lookup_expr='iexact')
    number_contains = django_filters.CharFilter(
        name='display_number_with_default', lookup_expr='icontains')

    class Meta:
        model = CourseOverview
        fields = ['display_name', 'org', 'number', 'number_contains', ]


class CourseEnrollmentFilter(django_filters.FilterSet):
    '''Provides filtering for the CourseEnrollment model objects

    '''
    course_id = django_filters.CharFilter(method='filter_course_id')
    is_active = django_filters.BooleanFilter(name='is_active',)

    def filter_course_id(self, queryset, name, value):
        '''

        This method converts the course id string to a CourseLocator object
        and returns the filtered queryset. This is required because
        CourseEnrollment course_id fields are of type CourseKeyField

        Query parameters with plus signs '+' in the string are automatically
        replaced with spaces, so we need to put the '+' back in for CourseKey
        to be able to create a course key object from the string
        '''
        course_key = as_course_key(value.replace(' ', '+'))
        return queryset.filter(course_id=course_key)

    class Meta:
        model = CourseEnrollment
        fields = ['course_id', 'user_id', 'is_active', ]
