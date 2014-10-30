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
import platform

# from constance import config

from celery import task

# from django.db.models import Q
# from django.core.exceptions import ObjectDoesNotExist
# from django.utils.translation import ugettext_lazy as _

# from sparks.foundations.classes import SimpleObject

# from oneflow.base.utils import RedisExpiringLock
# from oneflow.base.utils.dateutils import benchmark

# from async_messages import message_user

from ..models.reldb import (
    SyncNode,
)
LOGGER = logging.getLogger(__name__)


@task(queue='low')
def sync_all_nodes(force=False, stop_on_exception=True):
    """ Sync all 1flow nodes.

    .. warning:: for now this task does nothing,
        except of creating the local node.
    """

    try:
        local_node = SyncNode.object.get(is_local_instance=True)

    except SyncNode.DoesNotExist:

        local_node = SyncNode(
            name=platform.node(),
            is_active=True,
            is_local_instance=True)

        local_node.save()

        # message_user(self.user,
        #              _(u'Readability JSON export format detected.'),
        #              constants.INFO)

        LOGGER.info(u'Local sync node created.')
