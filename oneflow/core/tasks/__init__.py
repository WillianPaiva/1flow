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
import time as pytime

from constance import config

from celery import task
from celery.signals import beat_init

from django.utils.translation import ugettext_lazy as _

from ..models.reldb import BaseFeed

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.dateutils import (today, timedelta,
                                          naturaldelta, benchmark)

from gr_import import clean_gri_keys

from mongo import refresh_all_mongo_feeds  # NOQA

from migration import migrate_all_mongo_data  # NOQA

from sync import sync_all_nodes  # NOQA

from refresh import refresh_all_feeds, refresh_all_mailaccounts  # NOQA

from throttle import throttle_feed_refresh  # NOQA

from checks import *  # NOQA

from reprocess import *  # NOQA

from archive import *  # NOQA

LOGGER = logging.getLogger(__name__)

SYNCHRONIZE_STATSD_LOCK_NAME = 'synchronize_statsd_gauges'


@task(queue='clean')
def clean_obsolete_redis_keys():
    """ Call in turn all redis-related cleaners. """

    start_time = pytime.time()

    if today() <= (config.GR_END_DATE + timedelta(days=1)):
        clean_gri_keys()

    LOGGER.info(u'clean_obsolete_redis_keys(): finished in %s.',
                naturaldelta(pytime.time() - start_time))


@task(queue='clean')
def synchronize_statsd_gauges(full=False, force=False):
    """ Synchronize all counters to statsd. """

    # from oneflow.core.stats import (
    #     synchronize_mongodb_statsd_articles_gauges,
    #     synchronize_mongodb_statsd_tags_gauges,
    #     synchronize_mongodb_statsd_websites_gauges,
    #     synchronize_mongodb_statsd_authors_gauges,
    # )

    from oneflow.core.dbstats import (
        synchronize_statsd_articles_gauges,
        synchronize_statsd_tags_gauges,
        synchronize_statsd_websites_gauges,
        synchronize_statsd_authors_gauges,
        synchronize_statsd_feeds_gauges,
        synchronize_statsd_subscriptions_gauges,
        synchronize_statsd_reads_gauges,
    )

    my_lock = RedisExpiringLock(SYNCHRONIZE_STATSD_LOCK_NAME, expire_time=3600)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(_(u'Forcing statsd gauges synchronization…'))

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'synchronize_statsd_gauges() is already locked, '
                           u'aborting.')
            return

    # with benchmark('synchronize_mongodb_statsd_gauges()'):
    #     try:
    #         synchronize_mongodb_statsd_articles_gauges(full=full)
    #         synchronize_mongodb_statsd_tags_gauges(full=full)
    #         synchronize_mongodb_statsd_websites_gauges(full=full)
    #         synchronize_mongodb_statsd_authors_gauges(full=full)
    #     except:
    #         LOGGER.exception(u'MongoDB stats failed at some point')

    with benchmark('synchronize_statsd_gauges()'):

        try:
            synchronize_statsd_articles_gauges(full=full)
            synchronize_statsd_tags_gauges(full=full)
            synchronize_statsd_websites_gauges(full=full)
            synchronize_statsd_authors_gauges(full=full)
            synchronize_statsd_feeds_gauges(full=full)
            synchronize_statsd_subscriptions_gauges(full=full)
            synchronize_statsd_reads_gauges(full=full)

        finally:
            my_lock.release()


# Allow to release the lock manually for testing purposes.
synchronize_statsd_gauges.lock = RedisExpiringLock(
    SYNCHRONIZE_STATSD_LOCK_NAME)


@beat_init.connect()
def clear_all_locks(conf=None, **kwargs):
    """ Clear all expiring locks when celery beat starts. """

    for key, value in globals().items():
        if hasattr(value, 'lock'):
            getattr(value, 'lock').release()

            LOGGER.info(u'Released %s() lock.', key)

    locked_count = 0

    for feed in BaseFeed.objects.filter(is_active=True, is_internal=False):
        released = feed.refresh_lock.release()

        if released:
            locked_count += 1

    if locked_count:
        LOGGER.info(u'Released %s feeds refresh locks.', locked_count)

    else:
        LOGGER.info(u'No feed refresh lock released.')
