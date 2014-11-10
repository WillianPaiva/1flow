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

from ..common import User
# from oneflow.base.utils.dateutils import now, timedelta
from common import (
    BROADCAST_CHOICES,
    NODE_PERMISSIONS,
    SYNC_STATUS,
    SYNC_STRATEGIES,
    generate_token,
    default_broadcast_choice,
    default_node_permission,
    default_sync_status,
    default_sync_strategy,
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
        max_length=32, null=True, blank=True, db_index=True,
        verbose_name=_(u'Node unique identifier'))

    user = models.ForeignKey(
        User, verbose_name=_(u'Creator'),
        blank=True, null=True
    )

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    date_last_seen = models.DateTimeField(verbose_name=_(u'Last seen'),
                                          null=True, blank=True)

    is_active = models.BooleanField(
        verbose_name=_(u'Active'),
        default=True, blank=True,
        help_text=_(u'Do we synchronize with this node?'))

    # TODO: think aboud these possibilities:
    #
    #   - for local instance, `status` means nothing and should
    #     never be changed. For remote nodes, it indicates the current
    #     status between us and them.
    #   - For remote nodes, it indicates the current status between us
    #     and them. The local instance status is `SYNCING`, while there
    #     is at least one remote currently syncing with us.
    #   - then `status` is representative, and is advertised to others,
    #     to help them decide if they should sync with us now, or not.
    #   - whatever they choose to do, the local instance can refuse to
    #     sync for various reasons (too loaded, etc)
    status = models.IntegerField(
        choices=SYNC_STATUS.get_choices(),
        default=default_sync_status, blank=True,
        verbose_name=_(u'Synchronization status'))

    sync_error = models.TextField(null=True, blank=True)

    permission = models.IntegerField(
        verbose_name=_(u'Permission'),
        choices=NODE_PERMISSIONS.get_choices(),
        blank=True, default=default_node_permission,
        help_text=_(u'Permission level you grant to this node. Set on '
                    u'local node, this defines the system-wide permission '
                    u'level of all nodes whose own level is set to “global”. '
                    u'Does not affect current sync process if '
                    u'already running.'))

    strategy = models.IntegerField(
        verbose_name=_(u'Strategy'),
        choices=SYNC_STRATEGIES.get_choices(),
        blank=True, default=default_sync_strategy,
        help_text=_(u'System-wide synchronization strategy of the local '
                    u'node. For remote nodes, the value advertises how '
                    u'we see them from the local node standpoint. You '
                    u'can change locally the value for bi-directional '
                    u'trusted nodes only. For others, the value is '
                    u'read-only.'))

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
        help_text=_(u'How is this node broadcasted to others from here? '
                    u'Set on local node, this defines the system-wide '
                    u'broadcast level of all nodes whose own level is '
                    u'set to “global”.'))

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

    if sync_node.pk is None and not sync_node.is_local_instance:
        return

    if sync_node.uuid is None:
        sync_node.uuid = generate_token()

    if sync_node.permission == NODE_PERMISSIONS.GLOBAL:
        sync_node.permission = NODE_PERMISSIONS.BASE

    if sync_node.strategy == SYNC_STRATEGIES.GLOBAL:
        sync_node.strategy = SYNC_STRATEGIES.PULL

    if sync_node.broadcast == BROADCAST_CHOICES.GLOBAL:
        sync_node.broadcast = BROADCAST_CHOICES.TRUSTED


pre_save.connect(syncnode_pre_save, sender=SyncNode)
