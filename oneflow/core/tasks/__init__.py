# -*- coding: utf-8 -*-
"""
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

from random import randrange
from constance import config

from celery import task

from django.utils.translation import ugettext_lazy as _

from ..models import Feed, feed_refresh_task

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.dateutils import (now, today, timedelta,
                                          naturaldelta, benchmark)

LOGGER = logging.getLogger(__name__)

# from common import User, REDIS

from gr_import import clean_gri_keys

# Import this one, so that celery can find it,
# Else it complains about a missing import.
from checks import global_checker_task  # NOQA


@task(queue='clean')
def clean_obsolete_redis_keys():
    """ Call in turn all redis-related cleaners. """

    start_time = pytime.time()

    if today() <= (config.GR_END_DATE + timedelta(days=1)):
        clean_gri_keys()

    LOGGER.info(u'clean_obsolete_redis_keys(): finished in %s.',
                naturaldelta(pytime.time() - start_time))


@task(queue='high')
def refresh_all_feeds(limit=None, force=False):
    """ Refresh all feeds (RSS/Mail/Twitter…). """

    if config.FEED_FETCH_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'Feed refresh disabled in configuration.')
        return

    # Be sure two refresh operations don't overlap, but don't hold the
    # lock too long if something goes wrong. In production conditions
    # as of 20130812, refreshing all feeds takes only a moment:
    # [2013-08-12 09:07:02,028: INFO/MainProcess] Task
    #       oneflow.core.tasks.refresh_all_feeds succeeded in 1.99886608124s.
    my_lock = RedisExpiringLock('refresh_all_feeds', expire_time=120)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(_(u'Forcing all feed refresh…'))

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'refresh_all_feeds() is already locked, aborting.')
            return

    feeds = Feed.objects.filter(closed__ne=True, is_internal__ne=True)

    if limit:
        feeds = feeds.limit(limit)

    # No need for caching and cluttering CPU/memory for a one-shot thing.
    feeds.no_cache()

    with benchmark('refresh_all_feeds()'):

        try:
            count = 0
            mynow = now()

            for feed in feeds:

                if feed.refresh_lock.is_locked():
                    LOGGER.info(u'Feed %s already locked, skipped.', feed)
                    continue

                interval = timedelta(seconds=feed.fetch_interval)

                if feed.last_fetch is None:

                    feed_refresh_task.delay(feed.id)

                    LOGGER.info(u'Launched immediate refresh of feed %s which '
                                u'has never been refreshed.', feed)

                elif force or feed.last_fetch + interval < mynow:

                    how_late = feed.last_fetch + interval - mynow
                    how_late = how_late.days * 86400 + how_late.seconds

                    if config.FEED_REFRESH_RANDOMIZE:
                        countdown = randrange(
                            config.FEED_REFRESH_RANDOMIZE_DELAY)

                        feed_refresh_task.apply_async((feed.id, force),
                                                      countdown=countdown)

                    else:
                        countdown = 0
                        feed_refresh_task.delay(feed.id, force)

                    LOGGER.info(u'%s refresh of feed %s %s (%s late).',
                                u'Scheduled randomized'
                                if countdown else u'Launched',
                                feed,
                                u' in {0}'.format(naturaldelta(countdown))
                                if countdown else u'in the background',
                                naturaldelta(how_late))
                    count += 1

        finally:
            my_lock.release()

        LOGGER.info(u'Launched %s refreshes out of %s feed(s) checked.',
                    count, feeds.count())


@task(queue='low')
def synchronize_statsd_gauges(full=False):
    """ Synchronize all counters to statsd. """

    from oneflow.core.stats import (
        synchronize_statsd_articles_gauges,
        synchronize_statsd_tags_gauges,
        synchronize_statsd_websites_gauges,
        synchronize_statsd_authors_gauges,
    )

    synchronize_statsd_articles_gauges(full=full)
    synchronize_statsd_tags_gauges(full=full)
    synchronize_statsd_websites_gauges(full=full)
    synchronize_statsd_authors_gauges(full=full)
