# -*- coding: utf-8 -*-

from transmeta import TransMeta

from django.db import models
from django.utils.translation import ugettext_lazy as _


class EmailContent(models.Model):
    __metaclass__ = TransMeta

    name    = models.CharField(_('Email name'),
                               max_length=128, unique=True)
    subject = models.CharField(_('Email subject'), max_length=256)
    body    = models.TextField(_('Email body'))

    def __unicode__(self):
        return _(u'{field_name}: {truncated_field_value}').format(
            field_name=self.name, truncated_field_value=self.subject[:30]
            + (self.subject[30:] and u'…'))

    class Meta:
        translate = ('subject', 'body', )
        verbose_name = _(u'Email content')
        verbose_name_plural = _(u'Emails contents')
