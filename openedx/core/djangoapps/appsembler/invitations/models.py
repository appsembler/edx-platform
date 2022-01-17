"""
A minimalist invitation package

TODO:

* Check with Omar on AlternativeDomain. This is not just for this app. The potential problem
is if it is possible to create an alternative domain on a different site.

`openedx.core.djangoapps.appsembler.sites.models.AlternativeDomain`
"""
import uuid
from django.contrib.sites.models import Site
from django.db import models
from model_utils.models import TimeStampedModel


class Invitation(TimeStampedModel):
    """
    if the invitation was used ("applied"), then we can clean up
    """
    email = models.EmailField(db_index=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    # used_on = models.DateTimeField()

    class Meta(object):
        unique_together = ['email', 'site']

    def __str__(self):
        return 'Invitation <{email}, {domain}>'.format(
            email=self.email, domain=self.site.domain)
