# -*- coding: utf-8 -*-
"""
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

import logging
import platform

# from constance import config

from django.db import models
from django.db.models.signals import pre_save  # , post_save, pre_delete

from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

# from oneflow.base.fields import TextRedisDescriptor
# from oneflow.base.utils import register_task_method

from sparks.django.models import ModelDiffMixin

# from oneflow.base.utils.dateutils import now, timedelta
from common import (
    BROADCAST_CHOICES,
    NODE_PERMISSIONS,
    generate_token,
    default_broadcast_choice,
    default_node_permission,
)

LOGGER = logging.getLogger(__name__)


__all__ = [
    'SyncNode',
]


class SyncNode(ModelDiffMixin):

    """ Structure representing a 1flow instance on the network.

    .. note:: there will be one for the local instance, which will
        be partially immutable.
    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Sync node')
        verbose_name_plural = _(u'Sync nodes')

    # —————————————————————————————————————————————————————————————————— Fields

    name = models.CharField(
        max_length=384, null=True, blank=True,
        verbose_name=_(u'Node name'))

    uri = models.CharField(
        max_length=384, blank=True, null=True, unique=True,
        verbose_name=_(u'Node current URI'))

    uuid = models.CharField(
        max_length=32, blank=True, unique=True,
        default=generate_token,
        verbose_name=_(u'Node unique identifier'))

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    date_last_seen = models.DateTimeField(verbose_name=_(u'Last seen'),
                                          null=True, blank=True)

    is_active = models.BooleanField(
        verbose_name=_(u'Active'),
        default=True, blank=True,
        help_text=_(u'Do we synchronize with this node?'))

    permission = models.IntegerField(
        verbose_name=_(u'Permission'),
        choices=NODE_PERMISSIONS.get_choices(),
        blank=True, default=default_node_permission,
        help_text=_(u'Permission level you give to this node. On local '
                    u'node, this defines the permission level of '
                    u'all nodes whose level is set to “global”. '
                    u'Does not affect current sync process if '
                    u'already running.'))

    local_token = models.CharField(
        verbose_name=_(u'Local token'),
        max_length=32, blank=True, default=generate_token,
        help_text=_(u'Give this token to the remote instance\'s '
                    u'administrator to grant them any permission '
                    u'level > BASE.'))

    remote_token = models.CharField(
        verbose_name=_(u'Remote Token'),
        max_length=32, blank=True, null=True,
        help_text=_(u'Type/Paste here the token transmitted by the remote '
                    u'instance administrator. This token determines which '
                    u'permission your machine has on the remote one.'))

    # There must be at most ONE row where this boolean is True, and
    # all other will have it set to False.
    # This instance must never be deleted, and must always be active.
    is_local_instance = models.BooleanField(
        verbose_name=_(u'Is local instance?'),
        default=False, blank=True,
        help_text=_(u'This field should not be edited, it is '
                    u'auto-determined upon creation'))

    broadcast = models.IntegerField(
        verbose_name=_(u'Broadcast status'),
        choices=BROADCAST_CHOICES.get_choices(),
        default=default_broadcast_choice, blank=True,
        help_text=_(u'How is this node broadcasted to others? On local '
                    u'node, this defines the broadcast level of all nodes '
                    u'whose level is set to “global”.'))

    # ————————————————————————————————————————————————————————— Python & Django

    def __unicode__(self):

        return _(u'{0} node {1} #{2}').format(
            _(u'Local') if self.is_local_instance else _(u'Remote'),
            self.uuid if self.name is None else self.name,
            self.id,
        )

    @classmethod
    def get_local_node(cls):

        try:
            return SyncNode.objects.get(is_local_instance=True)

        except SyncNode.DoesNotExist:

            local_node = SyncNode(
                name=platform.node(),
                is_active=True,
                is_local_instance=True)

            local_node.save()

            return local_node


# ————————————————————————————————————————————————————————————————————— Signals


def syncnode_pre_save(instance, **kwargs):
    """ Be sure the local admin doesn't shoot {him,her}self in the foot. """

    sync_node = instance

    if sync_node.pk is None:
        return

    if sync_node.is_local_instance:
        if sync_node.permission == NODE_PERMISSIONS.GLOBAL:
            sync_node.permission = NODE_PERMISSIONS.BASE

        if sync_node.broadcast == BROADCAST_CHOICES.GLOBAL:
            sync_node.broadcast = BROADCAST_CHOICES.TRUSTED


pre_save.connect(syncnode_pre_save, sender=SyncNode)
