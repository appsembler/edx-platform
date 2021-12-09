
from lms.djangoapps.grades.rest_api.v1.views import CourseGradesView
from openedx.core.djangoapps.appsembler.grades_api.permissions import IsAMCAdmin
#from lms.djangoapps.grades.rest_api.v1.gradebook_views import 
from edx_rest_framework_extensions import permissions

class TahoeCourseGradesView(CourseGradesView):
    permission_classes = (IsAMCAdmin,)