
from contentstore.courseware_index import (
    CourseAboutSearchIndexer,
    CoursewareSearchIndexer,
)

from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore

def reindex_course(course_id):
    """
    Arguments:
    	course_id - The course id for a course. This is the 'course_id' property
    	            for the course as returend from:
    	            	<lms-host>/api/courses/v1/courses/

    Raises:
    	InvalidKeyError - if the opaque course 
    	SearchIndexingError - If the reindexing fails

    References
        course.py#reindex_course_and_check_access

    """
    course_key = CourseKey.from_string(course_id)
    with modulestore().bulk_operations(course_key):
        return CoursewareSearchIndexer.do_course_reindex(modulestore(),
            course_key)

def register_facet(facet_slug):
    """This method is a simple wrapper to abstract the  call. We use the facet
    slug instead of the facet id because new a new facet may not be in the
    database when it needs to be registered
    """
    return  CourseAboutSearchIndexer.add_facet({ 'slug': facet_slug })
