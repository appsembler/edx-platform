
from organizations.models import Organization, OrganizationCourse

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview


def get_course_keys_for_site(site):
    orgs = Organization.objects.filter(sites__in=[site])
    org_courses = OrganizationCourse.objects.filter(
        organization__in=orgs)
    course_ids = org_courses.values_list('course_id', flat=True)

    return [as_course_key(cid) for cid in course_ids]


def get_courses_for_site(site):
    course_keys = get_course_keys_for_site(site)
    courses = CourseOverview.objects.filter(id__in=course_keys)
    return courses
