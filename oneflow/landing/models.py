# -*- coding: utf-8 -*-

from transmeta import TransMeta

from django.utils.translation import ugettext_lazy as _
from django.db import models


class LandingContent(models.Model):
    __metaclass__ = TransMeta

    name    = models.CharField(max_length=128)
    content = models.TextField()

    def __unicode__(self):
        return _(u'{field_name}: {truncated_field_value}').format(
            field_name=self.name, truncated_field_value=self.content[:30]
            + (self.content[30:] and u'…'))

    class Meta:
        translate = ('content', )
