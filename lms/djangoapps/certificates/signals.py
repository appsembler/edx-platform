""" Signal handler for enabling self-generated certificates by default
for self-paced courses.
"""
from celery.task import task
from django.dispatch.dispatcher import receiver

from .config import waffle
from certificates.models import CertificateGenerationCourseSetting, \
    GeneratedCertificate
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.signals.signals import COURSE_GRADE_NOW_PASSED
from xmodule.modulestore.django import SignalHandler


@receiver(SignalHandler.course_published)
def _listen_for_course_publish(sender, course_key, **kwargs):  # pylint: disable=unused-argument
    """ Catches the signal that a course has been published in Studio and
    enable the self-generated certificates by default for self-paced
    courses.
    """
    enable_self_generated_certs.delay(unicode(course_key))


@task()
def enable_self_generated_certs(course_key):
    """Enable the self-generated certificates by default for self-paced courses."""
    course_key = CourseKey.from_string(course_key)
    course = CourseOverview.get_from_id(course_key)
    is_enabled_for_course = CertificateGenerationCourseSetting.is_enabled_for_course(course_key)
    if course.self_paced and not is_enabled_for_course:
        CertificateGenerationCourseSetting.set_enabled_for_course(course_key, True)


@receiver(COURSE_GRADE_NOW_PASSED, dispatch_uid="new_passing_learner")
def _listen_for_passing_grade(sender, user, course_key, **kwargs):  # pylint: disable=unused-argument
    """
    Listen for a learner passing a course, send cert generation task,
    downstream signal from COURSE_GRADE_CHANGED
    """
    # No flags enabled
    if (
        not waffle.waffle().is_enabled(waffle.SELF_PACED_ONLY) and
        not waffle.waffle().is_enabled(waffle.INSTRUCTOR_PACED_ONLY)
    ):
        return

    from courseware import courses

    # Only SELF_PACED_ONLY flag enabled
    if waffle.waffle().is_enabled(waffle.SELF_PACED_ONLY):
        if not courses.get_course_by_id(course_key, depth=0).self_paced:
            return
    # Only INSTRUCTOR_PACED_ONLY flag enabled
    elif waffle.waffle().is_enabled(waffle.INSTRUCTOR_PACED_ONLY):
        if courses.get_course_by_id(course_key, depth=0).self_paced:
            return
    if GeneratedCertificate.certificate_for_student(user, course_key) is None:
        from certificates import api as certs_api  # have to delay import
        certs_api.generate_user_certificates(user, course_key, generation_mode='self')
        log.info(u'Certificate generation task initiated for {user} : {course} via passing grade'.format(
            user=user.id,
            course=course_key
        ))
