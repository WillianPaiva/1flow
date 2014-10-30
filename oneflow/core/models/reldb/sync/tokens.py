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

import logging


from django.db import models
from django.utils.translation import ugettext_lazy as _

from common import NODE_PERMISSIONS, generate_token, default_node_permission
from node import SyncNode

LOGGER = logging.getLogger(__name__)


__all__ = [
    'NodePermissions',
]


class NodePermissions(models.Model):

    """ Allow to define custom token for fine-grained model-based permissions.
    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Model node permission')
        verbose_name_plural = _(u'Model node permissions')

    node = models.ForeignKey(
        SyncNode,
        verbose_name=_(u'Sync node'),
        null=True, blank=True,
        help_text=_(u'Set to no node to default the default permission '
                    u'for all nodes that do not have any specific permission.'))

    # TODO: implement node group.

    permission = models.IntegerField(
        verbose_name=_(u'Permission'),
        choices=NODE_PERMISSIONS.get_choices(),
        blank=True, default=default_node_permission,
        help_text=_(u'Give this token to the remote instance\'s '
                    u'administrator to give them read permission '
                    u'to this model.'))

    token = models.CharField(
        verbose_name=_(u'Token'),
        max_length=32, blank=True, default=generate_token,
        help_text=_(u'Give this token to the remote instance\'s '
                    u'administrator to give them read permission '
                    u'to this model.'))
