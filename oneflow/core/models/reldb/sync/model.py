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
# import operator

# from datetime import datetime

import logging

# from constance import config
# from django.conf import settings

from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

# from sparks.django.models import ModelDiffMixin
from sparks.django.utils import NamedTupleChoices

# from oneflow.base.fields import TextRedisDescriptor
# from oneflow.base.utils.dateutils import now, timedelta

from oneflow.base.utils import (
    # register_task_method,
    RedisExpiringLock,
)

# from common import REDIS, long_in_the_past, DjangoUser
from node import SyncNode
from tokens import NodeTokens


LOGGER = logging.getLogger(__name__)


__all__ = [
    'ModelSyncLayer',
]


class ModelSyncLayer(models.Model):

    """ Necessary glue-stuff to synchronize any model remotely. """

    SYNC_STATUS = NamedTupleChoices(
        'SYNC_STATUS',

        ('AUTH_WAIT', 99, _(u'Waiting for authorization')),

        ('IDLE', 0, _(u'Idle')),

        ('SYNCHRONIZING', 1, _(u'Synchronizing')),
        # ('RESYNC', 2, _(u'Re-synchronizing')),

        ('FAILED', 9, _(u'Synchronization failed')),
    )

    class Meta:
        abstract = True
        app_label = 'core'
        verbose_name = _(u'Synchronized model')
        verbose_name_plural = _(u'Synchronized models')

    # —————————————————————————————————————————————————————————————— Attributes

    prefered_node = models.ForeignKey(
        SyncNode, verbose_name=_(u'Prefered node'),
        null=True, blank=True)

    last_node = models.ForeignKey(
        SyncNode, verbose_name=_(u'Last node used'),
        null=True, blank=True)

    date_last_sync = models.DateTimeField(
        verbose_name=_(u'Last synchronization date'),
        null=True, blank=True)

    is_sync_active = models.BooleanField(
        verbose_name=_(u'Active'),
        default=True, blank=True,
        help_text=_(u'Do we currently synchronize this model?'))

    sync_status = models.IntegerField(
        choices=SYNC_STATUS.get_choices(),
        default=SYNC_STATUS.AUTH_WAIT, blank=True,
        verbose_name=_(u'Synchronization status'))

    sync_error = models.CharField(max_length=255)

    nodes = models.ManyToMany(NodeTokens, null=True, blank=True,
                              verbose_name=_(u'Nodes tokens'))

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def sync_lock(self):

        try:
            return self._sync_lock_

        except AttributeError:
            self._sync_lock_ = RedisExpiringLock(self, lock_name='sync',
                                                 expire_time=86100)
            return self._sync_lock_
