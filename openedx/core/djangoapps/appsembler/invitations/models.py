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

# May not need to 
# 


class Invitation(TimeStampedModel):
    email = models.EmailField(db_index=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)

    class Meta(object):
        unique_together = ['email', 'site']

    def __str__(self):
        return 'Invitation <{email}, {domain}>'.format(
            email=self.email, domain=self.site.domain)
