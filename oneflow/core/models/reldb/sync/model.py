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

# from oneflow.base.fields import TextRedisDescriptor
# from oneflow.base.utils.dateutils import now, timedelta

from oneflow.base.utils import (
    # register_task_method,
    RedisExpiringLock,
)

# from common import REDIS, long_in_the_past, DjangoUser
from common import (
    SYNC_STATUS,
    SYNC_STRATEGIES,
    default_sync_status,
    default_sync_strategy,
)
from node import SyncNode
from tokens import NodePermissions


LOGGER = logging.getLogger(__name__)


__all__ = [
    'ModelSyncLayer',
]


class ModelSyncLayer(models.Model):

    """ Necessary glue-stuff to synchronize any model remotely.

    .. note:: all fields / properties names must contain `sync`, to
        distinguish with other model attributes coming from other
        classes / mixins.
    """

    class Meta:
        abstract = True
        app_label = 'core'
        verbose_name = _(u'Synchronized model')
        verbose_name_plural = _(u'Synchronized models')

    # —————————————————————————————————————————————————————————————— Attributes

    prefered_sync_nodes = models.ManyToManyField(
        SyncNode, verbose_name=_(u'Prefered nodes'),
        null=True, blank=True,
        help_text=_(u'Put here the nodes you want yours '
                    u'to sync onto in priority.'))

    last_sync_node = models.ForeignKey(
        SyncNode, verbose_name=_(u'Last node used'),
        null=True, blank=True)

    date_last_sync = models.DateTimeField(
        verbose_name=_(u'Last synchronization date'),
        null=True, blank=True)

    sync_status = models.IntegerField(
        choices=SYNC_STATUS.get_choices(),
        default=default_sync_status, blank=True,
        verbose_name=_(u'Synchronization status'))

    sync_error = models.TextField(null=True, blank=True)

    sync_strategy = models.IntegerField(
        verbose_name=_(u'Strategy'),
        choices=SYNC_STRATEGIES.get_choices(),
        blank=True, default=default_sync_strategy,
        help_text=_(u'Synchronization strategy advertised by the node. '
                    u'On local node, this defines the system-wide '
                    u'strategy for all models whose value is set to '
                    u'“global”. Does not affect current sync process if '
                    u'already running.'))

    sync_permissions = models.ManyToManyField(
        NodePermissions,
        null=True, blank=True,
        verbose_name=_(u'Nodes permissions'),
        help_text=_(u'Define here global or fine-grained model-level '
                    u'permissions for synchronization nodes (only relevant '
                    u'if you set fine-grained permissions at the global '
                    u'level, or at least for one host.'))

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def sync_lock(self):

        try:
            return self._sync_lock_

        except AttributeError:
            self._sync_lock_ = RedisExpiringLock(self, lock_name='sync',
                                                 expire_time=86100)
            return self._sync_lock_
