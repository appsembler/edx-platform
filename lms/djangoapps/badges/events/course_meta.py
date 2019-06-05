"""
Events which have to do with a user doing something with more than one course, such
as enrolling in a certain number, completing a certain number, or completing a specific set of courses.
"""

from django.conf import settings
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

from badges.models import CourseEventBadgesConfiguration, BadgeClass
from badges.utils import requires_badges_enabled
from badges.events.course_complete import evidence_url


def award_badge(config, count, user, evidence=None):
    """
    Given one of the configurations for enrollments or completions, award
    the appropriate badge if one is configured.

    config is a dictionary with integer keys and course keys as values.
    count is the key to retrieve from this dictionary.
    user is the user to award the badge to.

    Example config:
        {3: 'slug_for_badge_for_three_enrollments', 5: 'slug_for_badge_with_five_enrollments'}
    """
    slug = config.get(count)
    if not slug:
        return
    badge_class = BadgeClass.get_badge_class(
        slug=slug, create=False,
    )
    if not badge_class:
        return
    if not badge_class.get_for_user(user):
        badge_class.award(user, evidence)


@requires_badges_enabled
def award_enrollment_badge(user):
    """
    Awards badges based on the number of courses a user is enrolled in.
    """
    # TODO: award badges on >= number enrolled
    config = CourseEventBadgesConfiguration.current().enrolled_settings
    enrollments = user.courseenrollment_set.filter(is_active=True).count()
    platform = configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
    evidence = [{"narrative": "Badge awarded for enrollment in {} courses on {}".format(enrollments, platform)}]
    award_badge(config, enrollments, user, evidence)


@requires_badges_enabled
def completion_check(user):
    """
    Awards badges based upon the number of courses a user has 'completed'.
    Courses are never truly complete, but they can be closed.

    For this reason we use checks on certificates to find out if a user has
    completed courses. This badge will not work if certificate generation isn't
    enabled and run.
    """
    # TODO: award badges on >= number completed
    from certificates.models import CertificateStatuses
    config = CourseEventBadgesConfiguration.current().completed_settings
    certificates = user.generatedcertificate_set.filter(status__in=CertificateStatuses.PASSED_STATUSES).count()
    platform = configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
    evidence = [{"narrative": "Badge awarded for completion of {} courses on {}".format(certificates, platform)}]
    award_badge(config, certificates, user, evidence)


@requires_badges_enabled
def course_group_check(user, course_key):
    """
    Awards a badge if a user has completed every course in a defined set.
    """
    from certificates.models import CertificateStatuses
    config = CourseEventBadgesConfiguration.current().course_group_settings
    awards = []
    for slug, keys in config.items():
        if course_key in keys:
            certs = user.generatedcertificate_set.filter(
                status__in=CertificateStatuses.PASSED_STATUSES,
                course_id__in=keys,
            )
            # >= to support case with multiple certs per course (enrollment in multiple modes)
            if len(certs) >= len(keys):
                evidence = [{'narrative': 'Certificate of course completion', 'url': evidence_url(user.id, key)} for key in keys]
                awards.append((slug, evidence))

    for award in awards:
        badge_class = BadgeClass.get_badge_class(
            slug=award[0], create=False,
        )
        if badge_class and not badge_class.get_for_user(user):
            badge_class.award(user, evidence=award[1])
