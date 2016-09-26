"""
This file contains implementation override of SearchResultProcessor which will allow
    * Blends in "location" property
    * Confirms user access to object
"""
from django.conf import settings
from django.core.urlresolvers import reverse

from opaque_keys.edx.locations import SlashSeparatedCourseKey
from search.result_processor import SearchResultProcessor
from lms.djangoapps.courseware.access import has_access
from microsite_configuration import microsite
from courseware.courses import get_course_by_id


class LmsCourseDiscoveryResultProcessor(SearchResultProcessor):
    """ SearchResultProcessor for LMS Search """
    _course_key = None

    def get_course_key(self):
        """ fetch course key object from string representation - retain result for subsequent uses """
        if self._course_key is None:
            self._course_key = SlashSeparatedCourseKey.from_deprecated_string(self._results_fields["course"])
        return self._course_key

    @property
    def url(self):
        """
        Property to display the url for the given location, useful for allowing navigation
        """
        if "course" not in self._results_fields or "id" not in self._results_fields:
            raise ValueError("Must have course and id in order to build url")

        return reverse(
            "jump_to",
            kwargs={"course_id": self._results_fields["course"], "location": self._results_fields["id"]}
        )

    def should_remove(self, user):
        """ Test to see if this result should be removed due to access restriction """
        if has_access(user, 'staff', self.get_course_key()):
            return False
        permission_name = microsite.get_value(
            'COURSE_CATALOG_VISIBILITY_PERMISSION',
            settings.COURSE_CATALOG_VISIBILITY_PERMISSION
        )
        try:
            course = get_course_by_id(self.get_course_key(), depth=0)
            if not has_access(user, permission_name, course):
                return True
        except:
            return True

        return False
