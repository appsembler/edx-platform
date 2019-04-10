""" Unit tests for enabling self-generated certificates by default
for self-paced courses.
"""
import mock

from certificates import api as certs_api
from certificates.config import waffle
from certificates.models import CertificateGenerationConfiguration
from certificates.signals import _listen_for_course_publish
from certificates.tasks import generate_certificate
from lms.djangoapps.course_blocks.api import get_course_blocks
from lms.djangoapps.grades.new.course_grade import CourseGradeFactory
from lms.djangoapps.grades.tests.utils import mock_get_score
from openedx.core.djangoapps.self_paced.models import SelfPacedConfiguration
from student.tests.factories import CourseEnrollmentFactory, UserFactory
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase


class SelfGeneratedCertsSignalTest(ModuleStoreTestCase):
    """ Tests for enabling self-generated certificates by default
    for self-paced courses.
    """

    def setUp(self):
        super(SelfGeneratedCertsSignalTest, self).setUp()
        SelfPacedConfiguration(enabled=True).save()
        self.course = CourseFactory.create(self_paced=True)
        # Enable the feature
        CertificateGenerationConfiguration.objects.create(enabled=True)

    def test_cert_generation_enabled_for_self_paced(self):
        """ Verify the signal enable the self-generated certificates by default for
        self-paced courses.
        """
        self.assertFalse(certs_api.cert_generation_enabled(self.course.id))

        _listen_for_course_publish('store', self.course.id)
        self.assertTrue(certs_api.cert_generation_enabled(self.course.id))


class PassingGradeCertsTest(ModuleStoreTestCase):
    """
    Tests for certificate generation task firing on passing grade receipt
    """
    def setUp(self):
        super(PassingGradeCertsTest, self).setUp()
        self.course = CourseFactory.create(self_paced=True)
        self.user = UserFactory.create()
        self.course_structure = get_course_blocks(self.user, self.course.location)
        self.enrollment = CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course.id,
            is_active=True,
            mode="verified",
        )
        self.ip_course = CourseFactory.create(self_paced=False)

    def test_cert_generation_on_passing_self_paced(self):
        with mock.patch(
            'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
            return_value=None
        ) as mock_generate_certificate_apply_async:
            with waffle.waffle().override(waffle.SELF_PACED_ONLY, active=True):
                grade_factory = CourseGradeFactory()
                with mock_get_score(0, 2):
                    grade_factory.update(self.user, self.course, self.course_structure)
                    mock_generate_certificate_apply_async.assert_not_called(
                        student=self.user,
                        course_key=self.course.id
                    )
                with mock_get_score(1, 2):
                    grade_factory.update(self.user, self.course, self.course_structure)
                    mock_generate_certificate_apply_async.assert_called(
                        student=self.user,
                        course_key=self.course.id
                    )
                # Certs are not re-fired after passing
                with mock_get_score(2, 2):
                    grade_factory.update(self.user, self.course, self.course_structure)
                    mock_generate_certificate_apply_async.assert_not_called(
                        student=self.user,
                        course_key=self.course.id
                    )
