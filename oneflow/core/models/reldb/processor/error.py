# -*- coding: utf-8 -*-
u"""
Copyright 2014 Olivier Cortès <oc@1flow.io>.

This file is part of the 1flow project.

1flow is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

1flow is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with 1flow.  If not, see http://www.gnu.org/licenses/
"""
# import uuid
import logging

from statsd import statsd
# from constance import config
from json_field import JSONField

from django.db import models
from django.db.models.signals import post_save, pre_delete  # , pre_save
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

# from ..common import DjangoUser as User  # ORIGINS,

# Avoid an import loop with chain.py
# from chaineditem import ChainedItem

LOGGER = logging.getLogger(__name__)


__all__ = [
    'ProcessingError',
]


# ————————————————————————————————————————————————————————————— Class & related


class ProcessingError(models.Model):

    """ Store processing errors in a dedicated table.

    This allows to sort them out more easily.

    Temporary errors should beretried with the same processing parameters
    from time to time. Definitive errors needs manual/human review to be
    fixed.

    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Processing error')
        verbose_name_plural = _(u'Processing errors')
        get_latest_by = 'date_created'

    instance_type = models.ForeignKey(ContentType, null=True, blank=True)
    instance_id = models.PositiveIntegerField(null=True, blank=True)
    instance = generic.GenericForeignKey('instance_type', 'instance_id')

    processor = models.ForeignKey('ChainedItem', related_name='errors',
                                  null=True, blank=True)
    chain = models.ForeignKey('ProcessingChain', related_name='errors',
                              null=True, blank=True)

    is_temporary = models.BooleanField(default=True,
                                       verbose_name=_(u'is temporary?'))

    date_created = models.DateTimeField(auto_now_add=True, blank=True,
                                        verbose_name=_(u'Date created'))
    date_updated = models.DateTimeField(auto_now=True, blank=True,
                                        verbose_name=_(u'Date updated'))

    exception = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Exception'),
        help_text=_(u'The full exception traceback. Can be a '
                    u'sentry ID or a full sentry URL if not '
                    u'using http://dev.1flow.net/'))

    issue_ref = models.CharField(
        max_length=256, verbose_name='Issue reference',
        null=True, blank=True,
        help_text=_(u'The official issue reference, if any. Can be '
                    u'anything like a Github issue#, a short issue URI '
                    u'or a fully qualified URI.'))

    notes = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Notes'),
        help_text=_(u'Things to know about this processor, '
                    u'in this chain, at this position.'))

    data = JSONField(default=dict, blank=True)

    # ————————————————————————————————————————————————————————— Python & Django

    def __unicode__(self):
        """ I'm __unicode__, pep257. """

        return u'{0} on {1} with {2} ({3})'.format(
            self.exception,
            self.instance,
            self.processor,
            self.id,
        )

    # ——————————————————————————————————————————————————————————— Class methods


# ————————————————————————————————————————————————————————————————————— Signals


# def chained_processor_pre_save(instance, **kwargs):
#     """ Method meant to be run from a celery task. """

#     return


def chained_processor_post_save(instance, **kwargs):

    if kwargs.get('created', False):
        statsd.gauge('processors.errors', 1, delta=True)


def chained_processor_pre_delete(instance, **kwargs):

    statsd.gauge('processors.errors', -1, delta=True)


# pre_save.connect(chained_processor_pre_save, sender=ProcessingError)
post_save.connect(chained_processor_post_save, sender=ProcessingError)
pre_delete.connect(chained_processor_pre_delete, sender=ProcessingError)
