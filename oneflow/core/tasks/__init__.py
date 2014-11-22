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

from ..models.reldb import (
    MailAccount,
    BaseFeed, basefeed_refresh_task
)

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.dateutils import (now, today, timedelta,
                                          naturaldelta, benchmark)

from gr_import import clean_gri_keys

from mongo import refresh_all_mongo_feeds  # NOQA
from migration import migrate_all_mongo_data  # NOQA
from sync import sync_all_nodes  # NOQA

# Import this one, so that celery can find it,
# Else it complains about a missing import.
from checks import *  # NOQA
from reprocess import *  # NOQA


LOGGER = logging.getLogger(__name__)

REFRESH_ALL_FEEDS_LOCK_NAME = 'refresh_all_feeds'
REFRESH_ALL_MAILACCOUNTS_LOCK_NAME = 'check_email_accounts'
SYNCHRONIZE_STATSD_LOCK_NAME = 'synchronize_statsd_gauges'


@task(queue='clean')
def clean_obsolete_redis_keys():
    """ Call in turn all redis-related cleaners. """

    start_time = pytime.time()

    if today() <= (config.GR_END_DATE + timedelta(days=1)):
        clean_gri_keys()

    LOGGER.info(u'clean_obsolete_redis_keys(): finished in %s.',
                naturaldelta(pytime.time() - start_time))


@task(queue='refresh')
def refresh_all_feeds(limit=None, force=False):
    u""" Refresh all feeds (RSS/Mail/Twitter…). """

    if config.FEED_FETCH_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'Feed refresh disabled in configuration.')
        return

    # Be sure two refresh operations don't overlap, but don't hold the
    # lock too long if something goes wrong. In production conditions
    # as of 20130812, refreshing all feeds takes only a moment:
    # [2013-08-12 09:07:02,028: INFO/MainProcess] Task
    #       oneflow.core.tasks.refresh_all_feeds succeeded in 1.99886608124s.
    #
    my_lock = RedisExpiringLock(
        REFRESH_ALL_FEEDS_LOCK_NAME,
        expire_time=config.FEED_GLOBAL_REFRESH_INTERVAL * 60 - 1
    )

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

    # This should bring us a Polymorphic Query to refresh all feeds types.
    feeds = BaseFeed.objects.filter(is_active=True, is_internal=False)

    if limit:
        feeds = feeds[:limit]

    with benchmark('refresh_all_feeds()'):

        try:
            count = 0
            mynow = now()

            for feed in feeds:

                if feed.refresh_lock.is_locked():
                    LOGGER.info(u'Feed %s already locked, skipped.', feed)
                    continue

                interval = timedelta(seconds=feed.fetch_interval)

                if feed.date_last_fetch is None:

                    basefeed_refresh_task.delay(feed.id)

                    LOGGER.info(u'Launched immediate refresh of feed %s which '
                                u'has never been refreshed.', feed)

                elif force or feed.date_last_fetch + interval < mynow:

                    how_late = feed.date_last_fetch + interval - mynow
                    how_late = how_late.days * 86400 + how_late.seconds

                    late = feed.date_last_fetch + interval < mynow

                    basefeed_refresh_task.delay(feed.id, force)

                    LOGGER.info(u'Launched refresh of feed %s (%s %s).',
                                feed, naturaldelta(how_late),
                                u'late' if late else u'earlier')
                    count += 1

        finally:
            # HEADS UP: in case the system is overloaded and feeds refresh()
            #           tasks don't complete fast enough, the current task
            #           will overload it even more. Thus, we intentionaly
            #           don't release the lock to avoid over-re-launched
            #           global tasks to feed the refresh queue with useless
            #           double-triple-Nble individual tasks.
            #
            # my_lock.release()
            pass

        LOGGER.info(u'Launched %s refreshes out of %s feed(s) checked.',
                    count, feeds.count())

# Allow to release the lock manually for testing purposes.
refresh_all_feeds.lock = RedisExpiringLock(REFRESH_ALL_FEEDS_LOCK_NAME)


@task(queue='refresh')
def refresh_all_mailaccounts(force=False):
    """ Check all unusable e-mail accounts. """

    if config.MAIL_ACCOUNT_REFRESH_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'E-mail accounts check disabled in configuration.')
        return

    accounts = MailAccount.objects.unusable()

    my_lock = RedisExpiringLock(REFRESH_ALL_MAILACCOUNTS_LOCK_NAME,
                                expire_time=30 * (accounts.count() + 2))

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(_(u'Forcing check of email accounts…'))

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'refresh_all_mailaccounts() is already locked, '
                           u'aborting.')
            return

    with benchmark('refresh_all_mailaccounts()'):

        try:
            for account in accounts:
                try:
                    account.test_connection()
                    account.update_mailboxes()

                except:
                    pass

        finally:
            my_lock.release()

        LOGGER.info(u'Launched %s checks on unusable accounts out of %s total.',
                    accounts.count(), MailAccount.objects.all().count())

# Allow to release the lock manually for testing purposes.
refresh_all_mailaccounts.lock = RedisExpiringLock(
    REFRESH_ALL_MAILACCOUNTS_LOCK_NAME)


@task(queue='clean')
def synchronize_statsd_gauges(full=False, force=False):
    """ Synchronize all counters to statsd. """

    from oneflow.core.stats import (
        synchronize_mongodb_statsd_articles_gauges,
        synchronize_mongodb_statsd_tags_gauges,
        synchronize_mongodb_statsd_websites_gauges,
        synchronize_mongodb_statsd_authors_gauges,
    )

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

    with benchmark('synchronize_mongodb_statsd_gauges()'):

        try:
            synchronize_mongodb_statsd_articles_gauges(full=full)
            synchronize_mongodb_statsd_tags_gauges(full=full)
            synchronize_mongodb_statsd_websites_gauges(full=full)
            synchronize_mongodb_statsd_authors_gauges(full=full)

        except:
            LOGGER.exception(u'MongoDB stats failed at some point')

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
