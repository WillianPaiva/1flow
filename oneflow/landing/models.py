# -*- coding: utf-8 -*-

from transmeta import TransMeta

from django.utils.translation import ugettext_lazy as _
from django.db import models


class LandingContent(models.Model):
    __metaclass__ = TransMeta

    name    = models.CharField(_('Template variable name'),
                               max_length=128, unique=True)
    content = models.TextField(_('Template variable content'))

    def __unicode__(self):
        return _(u'{field_name}: {truncated_field_value}').format(
            field_name=self.name, truncated_field_value=self.content[:30]
            + (self.content[30:] and u'…'))

    class Meta:
        translate = ('content', )
        verbose_name = _(u'Landing page content')
        verbose_name_plural = _(u'Landing page contents')
