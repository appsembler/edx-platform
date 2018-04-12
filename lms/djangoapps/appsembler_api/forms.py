from django.forms import CharField

from lms.djangoapps.course_api.forms import CourseListGetForm


class CourseListGetAndSearchForm(CourseListGetForm):
    """
    Similar to CourseListGetForm but with additional search argument.
    """

    search_term = CharField(required=False)
