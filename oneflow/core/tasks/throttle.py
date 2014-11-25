# -*- coding: utf-8 -*-
u"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

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

from constance import config

from celery import task

from django.utils.translation import ugettext_lazy as _

from ..models.reldb import BaseFeed

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.stats import (
    rabbitmq_queues,
    postgresql_relations_sizes
)

from refresh import refresh_all_feeds

LOGGER = logging.getLogger(__name__)

THROTTLE_REFRESH_LOCK_NAME = 'throttle_feed_refresh'


@task(name='oneflow.core.tasks.throttle_feed_refresh', queue='default')
def throttle_feed_refresh(force=False):
    u""" Be sure we don't overflow queues uselessly. """

    if config.FEED_FETCH_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'Feed refresh disabled in configuration.')
        return

    my_lock = RedisExpiringLock(
        THROTTLE_REFRESH_LOCK_NAME,
        expire_time=58
    )

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(_(u'Forcing feed refresh throttling…'))

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'refresh_all_feeds() is already locked, aborting.')
            return

    queues = {
        q['name']: q['backing_queue_status']['len']
        for q in rabbitmq_queues()
    }

    relations = {
        r[0]: r[1] for r in postgresql_relations_sizes()
    }

    feed_qitems = queues['refresh']

    feeds_count = relations[BaseFeed._meta.db_table]

    try:
        if feed_qitems > feeds_count:

            try:
                refresh_all_feeds.lock.release()
            except:
                pass
            refresh_all_feeds.lock.acquire()

            LOGGER.warning(u'Throttled feed refresh because queue items '
                           u'is going too high (%s > %s)',
                           feed_qitems, feeds_count)
        else:
            LOGGER.debug(u'Not throttled, items=%s <= feeds=%s.',
                         feed_qitems, feeds_count)
    finally:
        my_lock.release()


# Allow to release the lock manually for testing purposes.
throttle_feed_refresh.lock = RedisExpiringLock(THROTTLE_REFRESH_LOCK_NAME)
