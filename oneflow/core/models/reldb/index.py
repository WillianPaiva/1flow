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
import operator

from datetime import datetime
from email import message_from_string
from email.header import decode_header

import imaplib
import logging

from collections import OrderedDict
from constance import config

from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from ....base.fields import TextRedisDescriptor
from ....base.utils import register_task_method, list_chunks

from sparks.django.models import ModelDiffMixin

from oneflow.base.utils.dateutils import (now, timedelta,
                                          email_date_to_datetime_tz)

from common import REDIS, long_in_the_past, DjangoUser
import mail_common as common

LOGGER = logging.getLogger(__name__)

__all__ = [
    'IndexNode',
]


class IndexNode(ModelDiffMixin):

    name = models.CharField(max_length=255,
                            verbose_name=_(u'INdex name'))
    uri = models.CharField(max_length=255,
                           verbose_name=_(u'Index URI'))
    token = models.CharField(max_length=255,
                             verbose_name=_(u'Authorization token'))
    is_active = models.BooleanField(verbose_name=_(u'Active'),
                                    default=True, blank=True,
                                    help_text=_(u'Do we synchronize with '
                                                u'this index?'))

    # There must be at most ONE row where this boolean is True, and
    # all other will have it set to False.
    # This instance must never be deleted, and must always be active.
    is_local_instance = models.BooleanField(default=False, blank=True)

    is_public = models.BooleanField(verbose_name=_(u'Active'),
                                    default=True, blank=True,
                                    help_text=_(u'Do we synchronize with '
                                                u'this index?'))


class RemoteModel(models.Model):
    index = models.ForeignKey(IndexNode)

    name = models.CharField(max_length=255,
                            verbose_name=_(u'Remote model name'))
    uri = models.CharField(max_length=255,
                           verbose_name=_(u'Remote model URI'))
    is_active = models.BooleanField(verbose_name=_(u'Active'),
                                    default=True, blank=True,
                                    help_text=_(u'Do we synchronize this '
                                                u'remote model locally?'))

    # sync_status = models.CharField(max_length=1, choices=, default=,
    #                                verbose_name=_(u'Synchronization status'))
    # sync_error = models.CharField(max_length=255)
    # date_last_sync =
