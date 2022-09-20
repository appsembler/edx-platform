"""
Tests for reset deadlines endpoint.
"""
import datetime
import ddt

from django.urls import reverse
from django.utils import timezone
from mock import patch

from common.djangoapps.course_modes.models import CourseMode
from common.djangoapps.student.models import CourseEnrollment
from lms.djangoapps.courseware.tests.helpers import MasqueradeMixin
from lms.djangoapps.course_home_api.tests.utils import BaseCourseHomeTests
from openedx.core.djangoapps.schedules.models import Schedule
from openedx.core.djangoapps.schedules.tests.factories import ScheduleFactory
from xmodule.modulestore.tests.factories import CourseFactory


@ddt.ddt
class ResetCourseDeadlinesViewTests(BaseCourseHomeTests, MasqueradeMixin):
    """
    Tests for reset deadlines endpoint.
    """
    def test_reset_deadlines(self):
        CourseEnrollment.enroll(self.user, self.course.id, CourseMode.VERIFIED)
        # Test correct post body
        response = self.client.post(reverse('course-experience-reset-course-deadlines'), {'course_key': self.course.id})
        self.assertEqual(response.status_code, 200)
        # Test body with incorrect body param
        response = self.client.post(reverse('course-experience-reset-course-deadlines'), {'course': self.course.id})
        self.assertEqual(response.status_code, 400)
        # Test body with additional incorrect body param
        response = self.client.post(
            reverse('course-experience-reset-course-deadlines'), {'course_key': self.course.id, 'invalid': 'value'}
        )
        self.assertEqual(response.status_code, 400)

    def test_reset_deadlines_with_masquerade(self):
        """ Staff users should be able to masquerade as a learner and reset the learner's schedule """
        course = CourseFactory.create(self_paced=True)
        student_username = self.user.username
        student_enrollment = CourseEnrollment.enroll(self.user, course.id)
        student_schedule = ScheduleFactory.create(
            start_date=timezone.now() - datetime.timedelta(days=100),
            enrollment=student_enrollment
        )
        staff_schedule = ScheduleFactory(
            start_date=timezone.now() - datetime.timedelta(days=30),
            enrollment__course__id=course.id,
            enrollment__user=self.staff_user,
        )

        self.switch_to_staff()
        self.update_masquerade(course=course, username=student_username)

        with patch('openedx.features.course_experience.api.v1.views.dates_banner_should_display',
                   return_value=(True, False)):
            self.client.post(reverse('course-experience-reset-course-deadlines'), {'course_key': course.id})
        updated_schedule = Schedule.objects.get(id=student_schedule.id)
        self.assertEqual(updated_schedule.start_date.date(), datetime.datetime.today().date())
        updated_staff_schedule = Schedule.objects.get(id=staff_schedule.id)
        self.assertEqual(updated_staff_schedule.start_date, staff_schedule.start_date)

    def test_post_unauthenticated_user(self):
        self.client.logout()
        response = self.client.post(reverse('course-experience-reset-course-deadlines'), {'course_key': self.course.id})
        self.assertEqual(response.status_code, 401)

    def test_mobile_get_banner_info(self):
        response = self.client.get(reverse('course-experience-course-deadlines-mobile', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'missed_deadlines')
        self.assertContains(response, 'missed_gated_content')
        self.assertContains(response, 'content_type_gating_enabled')
        self.assertContains(response, 'verified_upgrade_link')

    def test_mobile_get_unknown_course(self):
        url = reverse('course-experience-course-deadlines-mobile', args=['course-v1:unknown+course+2T2020'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_mobile_get_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get(reverse('course-experience-course-deadlines-mobile', args=[self.course.id]))
        self.assertEqual(response.status_code, 401)
