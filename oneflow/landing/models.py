
from transmeta import TransMeta

from django.db import models


class LandingContent(models.Model):
    __metaclass__ = TransMeta

    name    = models.CharField(max_length=128)
    content = models.TextField()

    class Meta:
        translate = ('content', )
