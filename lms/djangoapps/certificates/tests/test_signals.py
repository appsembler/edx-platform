"""
Unit tests for enabling self-generated certificates for self-paced courses
and disabling for instructor-paced courses.
"""


import ddt
import mock
import six

from django.conf import settings

from lms.djangoapps.certificates import api as certs_api
from lms.djangoapps.certificates.models import (
    CertificateGenerationConfiguration,
    CertificateStatuses,
    CertificateWhitelist,
    GeneratedCertificate
)
from lms.djangoapps.certificates.signals import CERTIFICATE_DELAY_SECONDS, fire_ungenerated_certificate_task
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades.tests.utils import mock_passing_grade
from lms.djangoapps.verify_student.models import IDVerificationAttempt, SoftwareSecurePhotoVerification
from openedx.core.djangoapps.certificates.config import waffle
from student.tests.factories import CourseEnrollmentFactory, UserFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


class SelfGeneratedCertsSignalTest(ModuleStoreTestCase):
    """
    Tests for enabling/disabling self-generated certificates according to course-pacing.
    """
    ENABLED_SIGNALS = ['course_published']

    def setUp(self):
        super(SelfGeneratedCertsSignalTest, self).setUp()
        CertificateGenerationConfiguration.objects.create(enabled=True)

    def test_cert_generation_flag_on_pacing_toggle(self):
        """
        Verify that signal enables or disables self-generated certificates
        according to course-pacing.
        """
        self.course = CourseFactory.create(self_paced=False, emit_signals=True)
        self.assertFalse(certs_api.cert_generation_enabled(self.course.id))

        self.course.self_paced = True
        self.store.update_item(self.course, self.user.id)
        self.assertTrue(certs_api.cert_generation_enabled(self.course.id))

        self.course.self_paced = False
        self.store.update_item(self.course, self.user.id)
        self.assertFalse(certs_api.cert_generation_enabled(self.course.id))


class WhitelistGeneratedCertificatesTest(ModuleStoreTestCase):
    """
    Tests for whitelisted student auto-certificate generation
    """

    def setUp(self):
        super(WhitelistGeneratedCertificatesTest, self).setUp()
        self.course = CourseFactory.create(self_paced=True)
        self.user = UserFactory.create()
        CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course.id,
            is_active=True,
            mode="verified",
        )
        self.ip_course = CourseFactory.create(self_paced=False)
        CourseEnrollmentFactory(
            user=self.user,
            course_id=self.ip_course.id,
            is_active=True,
            mode="verified",
        )

    def test_cert_generation_on_whitelist_append_self_paced(self):
        """
        Verify that signal is sent, received, and fires task
        based on 'AUTO_CERTIFICATE_GENERATION' flag
        """
        with mock.patch(
            'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
            return_value=None
        ) as mock_generate_certificate_apply_async:
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=False):
                CertificateWhitelist.objects.create(
                    user=self.user,
                    course_id=self.course.id
                )
                mock_generate_certificate_apply_async.assert_not_called()
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=True):
                CertificateWhitelist.objects.create(
                    user=self.user,
                    course_id=self.course.id
                )
                mock_generate_certificate_apply_async.assert_called_with(
                    countdown=CERTIFICATE_DELAY_SECONDS,
                    kwargs={
                        'student': six.text_type(self.user.id),
                        'course_key': six.text_type(self.course.id),
                    }
                )

    def test_cert_generation_on_whitelist_append_instructor_paced(self):
        """
        Verify that signal is sent, received, and fires task
        based on 'AUTO_CERTIFICATE_GENERATION' flag
        """
        with mock.patch(
                'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
                return_value=None
        ) as mock_generate_certificate_apply_async:
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=False):
                CertificateWhitelist.objects.create(
                    user=self.user,
                    course_id=self.ip_course.id
                )
                mock_generate_certificate_apply_async.assert_not_called()
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=True):
                CertificateWhitelist.objects.create(
                    user=self.user,
                    course_id=self.ip_course.id
                )
                mock_generate_certificate_apply_async.assert_called_with(
                    countdown=CERTIFICATE_DELAY_SECONDS,
                    kwargs={
                        'student': six.text_type(self.user.id),
                        'course_key': six.text_type(self.ip_course.id),
                    }
                )


class PassingGradeCertsTest(ModuleStoreTestCase):
    """
    Tests for certificate generation task firing on passing grade receipt
    """

    def setUp(self):
        super(PassingGradeCertsTest, self).setUp()
        self.course = CourseFactory.create(
            self_paced=True,
        )
        self.user = UserFactory.create()
        self.enrollment = CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course.id,
            is_active=True,
            mode="verified",
        )
        self.ip_course = CourseFactory.create(self_paced=False)
        self.ip_enrollment = CourseEnrollmentFactory(
            user=self.user,
            course_id=self.ip_course.id,
            is_active=True,
            mode="verified",
        )
        attempt = SoftwareSecurePhotoVerification.objects.create(
            user=self.user,
            status='submitted'
        )
        attempt.approve()

    def test_cert_generation_on_passing_self_paced(self):
        with mock.patch(
            'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
            return_value=None
        ) as mock_generate_certificate_apply_async:
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=True):
                grade_factory = CourseGradeFactory()
                # Not passing
                grade_factory.update(self.user, self.course)
                mock_generate_certificate_apply_async.assert_not_called()
                # Certs fired after passing
                with mock_passing_grade():
                    grade_factory.update(self.user, self.course)
                    mock_generate_certificate_apply_async.assert_called_with(
                        countdown=CERTIFICATE_DELAY_SECONDS,
                        kwargs={
                            'student': six.text_type(self.user.id),
                            'course_key': six.text_type(self.course.id),
                        }
                    )

    def test_cert_generation_on_passing_instructor_paced(self):
        with mock.patch(
            'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
            return_value=None
        ) as mock_generate_certificate_apply_async:
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=True):
                grade_factory = CourseGradeFactory()
                # Not passing
                grade_factory.update(self.user, self.ip_course)
                mock_generate_certificate_apply_async.assert_not_called()
                # Certs fired after passing
                with mock_passing_grade():
                    grade_factory.update(self.user, self.ip_course)
                    mock_generate_certificate_apply_async.assert_called_with(
                        countdown=CERTIFICATE_DELAY_SECONDS,
                        kwargs={
                            'student': six.text_type(self.user.id),
                            'course_key': six.text_type(self.ip_course.id),
                        }
                    )

    def test_cert_already_generated(self):
        with mock.patch(
                'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
                return_value=None
        ) as mock_generate_certificate_apply_async:
            grade_factory = CourseGradeFactory()
            # Create the certificate
            GeneratedCertificate.eligible_certificates.create(
                user=self.user,
                course_id=self.course.id,
                status=CertificateStatuses.downloadable
            )
            # Certs are not re-fired after passing
            with mock_passing_grade():
                grade_factory.update(self.user, self.course)
                mock_generate_certificate_apply_async.assert_not_called()


@ddt.ddt
class FailingGradeCertsTest(ModuleStoreTestCase):
    """
    Tests for marking certificate notpassing when grade goes from passing to failing,
    and that the signal has no effect on the cert status if the cert has a non-passing
    status
    """

    def setUp(self):
        super(FailingGradeCertsTest, self).setUp()
        self.course = CourseFactory.create(
            self_paced=True,
        )
        self.user = UserFactory.create()
        self.enrollment = CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course.id,
            is_active=True,
            mode="verified",
        )
        attempt = SoftwareSecurePhotoVerification.objects.create(
            user=self.user,
            status='submitted'
        )
        attempt.approve()

    @ddt.data(
        CertificateStatuses.deleted,
        CertificateStatuses.deleting,
        CertificateStatuses.downloadable,
        CertificateStatuses.error,
        CertificateStatuses.generating,
        CertificateStatuses.notpassing,
        CertificateStatuses.restricted,
        CertificateStatuses.unavailable,
        CertificateStatuses.auditing,
        CertificateStatuses.audit_passing,
        CertificateStatuses.audit_notpassing,
        CertificateStatuses.unverified,
        CertificateStatuses.invalidated,
        CertificateStatuses.requesting,
    )
    def test_cert_failure(self, status):
        if CertificateStatuses.is_passing_status(status):
            expected_status = CertificateStatuses.notpassing
        else:
            expected_status = status
        GeneratedCertificate.eligible_certificates.create(
            user=self.user,
            course_id=self.course.id,
            status=status
        )
        CourseGradeFactory().update(self.user, self.course)
        cert = GeneratedCertificate.certificate_for_student(self.user, self.course.id)
        self.assertEqual(cert.status, expected_status)


@ddt.ddt
class FailingGradeCertsTestWithWhiteLabelCert(ModuleStoreTestCase):
    """
    Tests for marking if a certificate is whitelisted it won't change from a
    passing status to notpassing when grade goes from passing to failing, we
    also test and that the signal has no effect on the cert status if the cert
    has a non-passing status
    """

    def setUp(self):
        super(FailingGradeCertsTestWithWhiteLabelCert, self).setUp()
        self.course = CourseFactory.create(
            self_paced=True,
        )
        self.user = UserFactory.create()
        self.enrollment = CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course.id,
            is_active=True,
            mode="verified",
        )
        self.whitelist_cert = CertificateWhitelist.objects.create(
            user=self.user,
            course_id=self.course.id,
            whitelist=True
        )
        attempt = SoftwareSecurePhotoVerification.objects.create(
            user=self.user,
            status='submitted'
        )
        attempt.approve()

    @ddt.data(
        CertificateStatuses.deleted,
        CertificateStatuses.deleting,
        CertificateStatuses.downloadable,
        CertificateStatuses.error,
        CertificateStatuses.generating,
        CertificateStatuses.notpassing,
        CertificateStatuses.restricted,
        CertificateStatuses.unavailable,
        CertificateStatuses.auditing,
        CertificateStatuses.audit_passing,
        CertificateStatuses.audit_notpassing,
        CertificateStatuses.unverified,
        CertificateStatuses.invalidated,
        CertificateStatuses.requesting,
    )
    def test_cert_failure(self, status):
        # we want to make sure the certificate status does not change
        # upon course change, since the certificate is whitelisted.
        expected_status = status
        GeneratedCertificate.eligible_certificates.create(
            user=self.user,
            course_id=self.course.id,
            status=status
        )
        CourseGradeFactory().update(self.user, self.course)
        cert = GeneratedCertificate.certificate_for_student(self.user, self.course.id)
        self.assertEqual(cert.status, expected_status)


class LearnerTrackChangeCertsTest(ModuleStoreTestCase):
    """
    Tests for certificate generation task firing on learner verification
    """

    def setUp(self):
        super(LearnerTrackChangeCertsTest, self).setUp()
        self.course_one = CourseFactory.create(self_paced=True)
        self.user_one = UserFactory.create()
        self.enrollment_one = CourseEnrollmentFactory(
            user=self.user_one,
            course_id=self.course_one.id,
            is_active=True,
            mode='verified',
        )
        self.user_two = UserFactory.create()
        self.course_two = CourseFactory.create(self_paced=False)
        self.enrollment_two = CourseEnrollmentFactory(
            user=self.user_two,
            course_id=self.course_two.id,
            is_active=True,
            mode='verified'
        )
        with mock_passing_grade():
            grade_factory = CourseGradeFactory()
            grade_factory.update(self.user_one, self.course_one)
            grade_factory.update(self.user_two, self.course_two)

    def test_cert_generation_on_photo_verification_self_paced(self):
        with mock.patch(
            'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
            return_value=None
        ) as mock_generate_certificate_apply_async:
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=True):
                mock_generate_certificate_apply_async.assert_not_called()
                attempt = SoftwareSecurePhotoVerification.objects.create(
                    user=self.user_one,
                    status='submitted'
                )
                attempt.approve()
                mock_generate_certificate_apply_async.assert_called_with(
                    countdown=CERTIFICATE_DELAY_SECONDS,
                    kwargs={
                        'student': six.text_type(self.user_one.id),
                        'course_key': six.text_type(self.course_one.id),
                        'expected_verification_status': IDVerificationAttempt.STATUS.approved,
                    }
                )

    def test_cert_generation_on_photo_verification_instructor_paced(self):
        with mock.patch(
            'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
            return_value=None
        ) as mock_generate_certificate_apply_async:
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=True):
                mock_generate_certificate_apply_async.assert_not_called()
                attempt = SoftwareSecurePhotoVerification.objects.create(
                    user=self.user_two,
                    status='submitted'
                )
                attempt.approve()
                mock_generate_certificate_apply_async.assert_called_with(
                    countdown=CERTIFICATE_DELAY_SECONDS,
                    kwargs={
                        'student': six.text_type(self.user_two.id),
                        'course_key': six.text_type(self.course_two.id),
                        'expected_verification_status': IDVerificationAttempt.STATUS.approved,
                    }
                )


@ddt.ddt
class CertificateGenerationTaskTest(ModuleStoreTestCase):
    """
    Tests for certificate generation task.
    """

    def setUp(self):
        super(CertificateGenerationTaskTest, self).setUp()
        self.course = CourseFactory.create()

    @ddt.data(
        ('professional', True),
        ('verified', True),
        ('no-id-professional', True),
        ('credit', True),
        ('masters', True),
        ('audit', False),
        ('honor', True),  # TAHOE_AUTO_GENERATE_HONOR_CERTS feature: allows for honor
    )
    @ddt.unpack
    @mock.patch.dict(settings.FEATURES, {'TAHOE_AUTO_GENERATE_HONOR_CERTS': True})
    def test_fire_ungenerated_certificate_task_allowed_modes(self, enrollment_mode, should_create):
        """
        Test that certificate generation task is fired for only modes that are
        allowed to generate certificates automatically.
        """
        self.user = UserFactory.create()
        self.enrollment = CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course.id,
            is_active=True,
            mode=enrollment_mode
        )
        with mock.patch(
            'lms.djangoapps.certificates.signals.generate_certificate.apply_async',
            return_value=None
        ) as mock_generate_certificate_apply_async:
            with waffle.waffle().override(waffle.AUTO_CERTIFICATE_GENERATION, active=True):
                fire_ungenerated_certificate_task(self.user, self.course.id)
                task_created = mock_generate_certificate_apply_async.called
                self.assertEqual(task_created, should_create)
