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

import uuid
# import operator

# from datetime import datetime

import logging

# from collections import OrderedDict
# from constance import config

from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

# from oneflow.base.fields import TextRedisDescriptor
# from oneflow.base.utils import register_task_method

from sparks.django.models import ModelDiffMixin
from sparks.django.utils import NamedTupleChoices

# from oneflow.base.utils.dateutils import now, timedelta

# from common import REDIS, long_in_the_past, DjangoUser


LOGGER = logging.getLogger(__name__)


__all__ = [
    'SyncNode',
    'generate_token',
]


def generate_token():
    """ Return an uuid4 hex token. """

    return uuid.uuid4().hex


class SyncNode(ModelDiffMixin):

    """ Structure representing a 1flow instance on the network.

    .. note:: there will be one for the local instance, which will
        be partially immutable.
    """

    BROADCAST_CHOICES = NamedTupleChoices(
        'BROADCAST_CHOICES',

        ('NONE', 0, _(u'No Broadcast')),
        ('TRUSTED', 1, _(u'To trusted instances only')),
        ('ALL', 2, _(u'To all instances')),
    )

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Sync node')
        verbose_name_plural = _(u'Sync nodes')

    # —————————————————————————————————————————————————————————————— Attributes

    name = models.CharField(
        max_length=384, null=True, blank=True,
        verbose_name=_(u'Node name'))

    uri = models.CharField(
        max_length=384, blank=True, null=True, unique=True,
        verbose_name=_(u'Node current URI'))

    uuid = models.CharField(
        max_length=32, blank=True, unique=True,
        verbose_name=_(u'Node unique identifier'))

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    local_read_token = models.CharField(
        verbose_name=_(u'Local read authorization token'),
        max_length=32, blank=True, default=generate_token,
        help_text=_(u'Give this token to the administrator of this remote '
                    u'instance to give it global read permission.'))

    local_write_token = models.CharField(
        verbose_name=_(u'Local write authorization token'),
        max_length=32, blank=True, default=generate_token,
        help_text=_(u'Give this token to the administrator of this remote '
                    u'instance to give it global write permission.'))

    remote_read_token = models.CharField(
        verbose_name=_(u'Remote read authorization token'),
        max_length=32, blank=True, null=True,
        help_text=_(u'Enter here the token given by the remote administrator '
                    u'to allow your instance global read access to theirs.'))

    remote_write_token = models.CharField(
        verbose_name=_(u'Remote write authorization token'),
        max_length=32, blank=True, null=True,
        help_text=_(u'Enter here the token given by the remote administrator '
                    u'to allow your instance global write access to theirs.'))

    is_active = models.BooleanField(
        verbose_name=_(u'Active'),
        default=True, blank=True,
        help_text=_(u'Do we synchronize with this index?'))

    # There must be at most ONE row where this boolean is True, and
    # all other will have it set to False.
    # This instance must never be deleted, and must always be active.
    is_local_instance = models.BooleanField(
        verbose_name=_(u'Is local instance?'),
        default=False, blank=True,
        help_text=_(u'This field should not be edited, it is '
                    u'auto-determined upon creation'))

    is_trusted = models.BooleanField(
        verbose_name=_(u'Is trusted?'),
        default=False, blank=True,
        help_text=_(u'Do we trust this instance? Enabling this allow to '
                    u'broadcast restricted indexes to friends but not all '
                    u'instances.'))

    broadcast = models.IntegerField(
        verbose_name=_(u'Broadcast status'),
        default=BROADCAST_CHOICES.TRUSTED, blank=True,
        help_text=_(u'Is this index broadcasted to others? This field is '
                    u'used only when the global config.SYNC_BROADCAST_INDEXES '
                    u'is already true, else it has no effect.'))

    # ——————————————————————————————————————————————————————————— Class methods
