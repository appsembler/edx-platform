"""
Constants for the credential_criteria Django app.
"""

from django.utils.translation import ugettext_lazy as _


# LMS
CREDENTIAL_CRITERION_TYPE_COMPLETION = u'Completion'
CREDENTIAL_CRITERION_TYPE_SCORE = u'Score'
CREDENTIAL_CRITERION_TYPE_GRADE = u'Letter Grade'
CREDENTIAL_CRITERION_TYPE_PASSFAIL = u'Pass/Fail'
CREDENTIAL_CRITERION_TYPE_ENROLLMENT = u'Enrollment'
CREDENTIAL_CRITERION_TYPE_CREDENTIAL = u'Credential'

# Studio
CREDENTIAL_CRITERION_TYPE_PUBLISH = u'Publication'


CREDENTIAL_CRITERION_TYPES = {
    CREDENTIAL_CRITERION_TYPE_COMPLETION,
    CREDENTIAL_CRITERION_TYPE_SCORE,
    CREDENTIAL_CRITERION_TYPE_GRADE,
    CREDENTIAL_CRITERION_TYPE_PASSFAIL,
    CREDENTIAL_CRITERION_TYPE_ENROLLMENT,
    CREDENTIAL_CRITERION_TYPE_CREDENTIAL,
    CREDENTIAL_CRITERION_TYPE_PUBLISH
}

CREDENTIAL_CRITERION_TYPE_VERBS = {
    CREDENTIAL_CRITERION_TYPE_COMPLETION: _("completed"),
    CREDENTIAL_CRITERION_TYPE_SCORE: _("scored at least {percent}%"),
    CREDENTIAL_CRITERION_TYPE_GRADE: _("achieved a grade of better than {letter_grade}"),
    CREDENTIAL_CRITERION_TYPE_PASSFAIL: _("passed"),
    CREDENTIAL_CRITERION_TYPE_ENROLLMENT: _("enrolled"),
    CREDENTIAL_CRITERION_TYPE_CREDENTIAL: _("earned"),
    CREDENTIAL_CRITERION_TYPE_PUBLISH: _("published"),
}
