"""
Models for store external courses info to display on ui
"""
from django.db import models


class ExternalCourseTile(models.Model):
    """
    This class stores all the information for the course retrieved from the
    courses API
    """
    course_key = models.CharField(unique=True, max_length=255, null=False, blank=False)
    title = models.CharField(max_length=255, null=False, blank=False)
    org = models.CharField(max_length=255, null=False, blank=False)
    course_link = models.URLField(null=False, blank=False)
    image_url = models.URLField(null=False, blank=False)
    starts = models.DateTimeField(null=False, blank=False)
    ends = models.DateTimeField(null=False, blank=False)
    pacing_type = models.CharField(max_length=255, null=False, blank=False)
    is_credit_eligible = models.BooleanField(default=False)
    is_verified_eligible = models.BooleanField(default=False)
    course_duration = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return "%s (%s)" % (self.title, self.org)

    @property
    def is_self_paced(self):
        return True if self.pacing_type == 'self_paced' else False

    @property
    def course_weeks_duration(self):
        if self.is_self_paced:
            return 'Self-Paced'
        else:
            weeks = int(self.ends.strftime("%V")) - int(self.starts.strftime("%V"))
            return '%s Week Commitment' % str(weeks)
