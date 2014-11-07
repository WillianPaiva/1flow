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

LOGGER = logging.getLogger(__name__)


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
        'refresh_all_feeds',
        expire_time=settings.FEED_GLOBAL_REFRESH_DELAY * 60
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
        feeds = feeds.limit(limit)

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

                    countdown = 0
                    basefeed_refresh_task.delay(feed.id, force)

                    LOGGER.info(u'%s refresh of feed %s %s (%s late).',
                                u'Scheduled randomized'
                                if countdown else u'Launched',
                                feed,
                                u' in {0}'.format(naturaldelta(countdown))
                                if countdown else u'in the background',
                                naturaldelta(how_late))
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


@task(queue='refresh')
def refresh_all_mailaccounts(force=False):
    """ Check all unusable e-mail accounts. """

    if config.MAIL_ACCOUNT_REFRESH_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'E-mail accounts check disabled in configuration.')
        return

    accounts = MailAccount.objects.filter(is_usable=False)

    my_lock = RedisExpiringLock('check_email_accounts',
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


@task(queue='clean')
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
