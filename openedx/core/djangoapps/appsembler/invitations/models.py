"""
A minimalist invitation package

TODO:

* Check with Omar on AlternativeDomain. This is not just for this app. The potential problem
is if it is possible to create an alternative domain on a different site
"""
import uuid
# from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.db import models
from model_utils.models import TimeStampedModel
from openedx.core.djangoapps.appsembler.sites.models import AlternativeDomain


class Invitation(TimeStampedModel):
    email = models.EmailField(db_index=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    # created = models.DateTimeField(verbose_name=_('created'),
    #                                default=timezone.now)

    class Meta(object):
        unique_together = ['email', 'site']
