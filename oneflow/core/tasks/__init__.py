# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

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
    License along with 1flow. If not, see http://www.gnu.org/licenses/

"""

import redis
import logging
import time as pytime

from random import randrange
from constance import config

from pymongo.errors import DuplicateKeyError
from mongoengine.fields import DBRef
from mongoengine.errors import NotUniqueError, ValidationError
from mongoengine.queryset import Q
from mongoengine.context_managers import no_dereference

from celery import task, chain as tasks_chain

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.mail import mail_managers
from django.utils.translation import ugettext_lazy as _

from .models import (RATINGS,
                     Article,
                     Feed, feed_refresh_task,
                     Subscription, Read, User as MongoUser)
from .stats import synchronize_statsd_articles_gauges

from ...base.utils import RedisExpiringLock
from ...base.utils.dateutils import (now, today, timedelta,
                                     naturaldelta, benchmark)

# other tasks
from google_reader_import import *  # NOQA

LOGGER = logging.getLogger(__name__)

REDIS = redis.StrictRedis(host=settings.REDIS_HOST,
                          port=settings.REDIS_PORT,
                          db=settings.REDIS_DB)


@task(queue='clean')
def clean_obsolete_redis_keys():
    """ Call in turn all redis-related cleaners. """

    start_time = pytime.time()

    if today() <= (config.GR_END_DATE + timedelta(days=1)):
        clean_gri_keys()

    LOGGER.info(u'clean_obsolete_redis_keys(): finished in %s.',
                naturaldelta(pytime.time() - start_time))

# •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Refresh RSS feeds


@task(queue='high')
def refresh_all_feeds(limit=None, force=False):

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


@task(queue='high')
def global_checker_task(*args, **kwargs):
    """ Just run all tasks in a celery chain, to avoid
        them to overlap and hit the database too much. """

    global_check_chain = tasks_chain(
        # HEADS UP: all subtasks are immutable, we just want them to run
        # chained to avoid dead times, without any link between them.

        # Begin by checking duplicates and archiving as much as we can,
        # for next tasks to work on the smallest-possible objects set.
        global_duplicates_checker.si(),
        archive_documents.si(),

        global_subscriptions_checker.si(),
        global_reads_checker.si(),
    )

    return global_check_chain.delay()


@task(queue='low')
def global_feeds_checker():

    def pretty_print_feed(feed):

        return (u'- %s,\n'
                u'    - admin url: http://%s%s\n'
                u'    - public url: %s\n'
                u'    - %s\n'
                u'    - reason: %s\n'
                u'    - last error: %s') % (
            feed,

            settings.SITE_DOMAIN,

            reverse('admin:%s_%s_change' % (
                feed._meta.get('app_label', 'nonrel'),
                feed._meta.get('module_name', 'feed')),
                args=[feed.id]),

            feed.url,

            (u'closed on %s' % feed.date_closed)
            if feed.date_closed
            else u'(no closing date)',

            feed.closed_reason or
            u'none (or manually closed from the admin interface)',

            feed.errors[0]
            if len(feed.errors)
            else u'(no error recorded)')

    dtnow        = now()
    limit_days   = config.FEED_CLOSED_WARN_LIMIT
    closed_limit = dtnow - timedelta(days=limit_days)

    feeds = Feed.objects(Q(closed=True)
                         & (Q(date_closed__exists=False)
                            | Q(date_closed__gte=closed_limit)))

    count = feeds.count()

    if count > 10000:
        # prevent CPU and memory hogging.
        LOGGER.info(u'Switching query to no_cache(), this will take longer.')
        feeds.no_cache()

    if not count:
        LOGGER.info('No feed was closed in the last %s days.', limit_days)
        return

    mail_managers(_(u'Reminder: {0} feed(s) closed in last '
                  u'{1} day(s)').format(count, limit_days),
                  _(u"\n\nHere is the list, dates (if any), and reasons "
                    u"(if any) of closing:\n\n{feed_list}\n\nYou can manually "
                    u"reopen any of them from the admin interface.\n\n").format(
                      feed_list='\n\n'.join(pretty_print_feed(feed)
                                            for feed in feeds)))

    start_time = pytime.time()

    # Close the feeds, but after sending the mail,
    # So that initial reason is displayed at least
    # once to a real human.
    for feed in feeds:
        if feed.date_closed is None:
            feed.close('Automatic close by periodic checker task')

    LOGGER.info('Closed %s feeds in %s.', count,
                naturaldelta(pytime.time() - start_time))


@task(queue='low')
def global_subscriptions_checker(force=False, limit=None, from_feeds=True,
                                 from_users=False, extended_check=False):
    """ A conditionned version of :meth:`Feed.check_subscriptions`. """

    if config.CHECK_SUBSCRIPTIONS_DISABLED:
        LOGGER.warning(u'Subscriptions checks disabled in configuration.')
        return

    # This task runs one a day. Acquire the lock for just a
    # little more time to avoid over-parallelized runs.
    my_lock = RedisExpiringLock('check_all_subscriptions',
                                expire_time=3600 * 25)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'Forcing subscriptions checks…')

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'global_subscriptions_checker() is already '
                           u'locked, aborting.')
            return

    if limit is None:
        limit = 0

    assert int(limit) >= 0

    try:
        if from_feeds:
            with benchmark("Check all subscriptions from feeds"):

                feeds           = Feed.good_feeds.no_cache()
                feeds_count     = feeds.count()
                processed_count = 0
                checked_count   = 0

                for feed in feeds:

                    if limit and checked_count > limit:
                        break

                    if extended_check:
                        feed.compute_cached_descriptors(all=True,
                                                        good=True,
                                                        bad=True)

                    # Do not extended_check=True, this would double-do
                    # the subscription.check_reads() already called below.
                    feed.check_subscriptions()

                    for subscription in feed.subscriptions:

                        processed_count += 1

                        if subscription.all_articles_count \
                                != feed.good_articles_count:

                            checked_count += 1

                            LOGGER.info(u'Subscription %s (#%s) has %s reads '
                                        u'whereas its feed has %s good '
                                        u'articles; checking…',
                                        subscription.name, subscription.id,
                                        subscription.all_articles_count,
                                        feed.good_articles_count)

                            subscription.check_reads(
                                force=True, extended_check=extended_check)

                LOGGER.info(u'%s/%s (limit:%s) feeds processed, %s '
                            u'checked (%.2f%%).',
                            processed_count, feeds_count, limit,
                            checked_count, checked_count
                            * 100.0 / processed_count)

        if from_users:
            with benchmark("Check all subscriptions from users"):

                users           = MongoUser.objects.all().no_cache()
                users_count     = users.count()
                processed_count = 0

                for user in users:

                    # Do not extended_check=True, this would double-do
                    # the subscription.check_reads() already called below.
                    user.check_subscriptions()

                    if extended_check:
                        user.compute_cached_descriptors(all=True,
                                                        unread=True,
                                                        starred=True,
                                                        bookmarked=True)

                        for subscription in user.subscriptions:
                                processed_count += 1

                                subscription.check_reads(force=True,
                                                         extended_check=True)

                LOGGER.info(u'%s users %sprocessed. '
                            u'All were checked.', users_count,
                            u'and %s subscriptions '.format(processed_count)
                            if extended_check else u'')

    finally:
        my_lock.release()


@task(queue='low')
def global_duplicates_checker(limit=None, force=False):
    """ Something that will ensure that duplicate articles have no more read
        anywhere, fix it if not, and update all counters accordingly. """

    if config.CHECK_DUPLICATES_DISABLED:
        LOGGER.warning(u'Duplicates check disabled in configuration.')
        return

    # This task runs one a day. Acquire the lock for just a
    # little more time to avoid over-parallelized runs.
    my_lock = RedisExpiringLock('check_all_duplicates', expire_time=3600 * 25)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'Forcing duplicates check…')

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'global_subscriptions_checker() is already '
                           u'locked, aborting.')
            return

    if limit is None:
        limit = 0

    duplicates = Article.objects(duplicate_of__ne=None).no_cache()

    total_dupes_count = duplicates.count()
    total_reads_count = 0
    processed_dupes   = 0
    done_dupes_count  = 0

    with benchmark(u"Check {0}/{1} duplicates".format(limit,
                   total_dupes_count)):

        try:
            for duplicate in duplicates:
                reads = Read.objects(article=duplicate)

                processed_dupes += 1

                if reads:
                    done_dupes_count  += 1
                    reads_count        = reads.count()
                    total_reads_count += reads_count

                    LOGGER.info(u'Duplicate article %s still has %s '
                                u'reads, fixing…', duplicate, reads_count)

                    duplicate.duplicate_of.replace_duplicate_everywhere(
                        duplicate.id)

                    if limit and done_dupes_count >= limit:
                        break

        finally:
            my_lock.release()

    LOGGER.info(u'global_duplicates_checker(): %s/%s duplicates processed '
                u'(%.2f%%), %s corrected (%.2f%%), %s reads altered.',
                processed_dupes, total_dupes_count,
                processed_dupes * 100.0 / total_dupes_count,
                done_dupes_count, done_dupes_count * 100.0 / processed_dupes,
                total_reads_count)


@task(queue='low')
def global_reads_checker(limit=None, force=False, verbose=False,
                         break_on_exception=False, extended_check=False):

    if config.CHECK_READS_DISABLED:
        LOGGER.warning(u'Reads check disabled in configuration.')
        return

    # This task runs twice a day. Acquire the lock for just a
    # little more time (13h, because Redis doesn't like floats)
    # to avoid over-parallelized runs.
    my_lock = RedisExpiringLock('check_all_reads', expire_time=3600 * 13)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'Forcing reads check…')

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'global_reads_checker() is already '
                           u'locked, aborting.')
            return

    if limit is None:
        limit = 0

    bad_reads = Read.objects(Q(is_good__exists=False)
                             | Q(is_good__ne=True)).no_cache()

    total_reads_count   = bad_reads.count()
    processed_reads     = 0
    wiped_reads_count   = 0
    changed_reads_count = 0
    skipped_count       = 0

    with benchmark(u"Check {0}/{1} reads".format(limit, total_reads_count)):
        try:
            for read in bad_reads:

                processed_reads += 1

                if limit and changed_reads_count >= limit:
                    break

                if read.is_good:
                    # This read has been activated via another
                    # one, attached to the same article.
                    changed_reads_count += 1
                    continue

                article = read.article

                if isinstance(article, DBRef) or article is None:
                    # The article doesn't exist anymore. Wipe the read.
                    wiped_reads_count += 1
                    LOGGER.error(u'Read #%s has dangling reference to '
                                 u'non-existing article #%s, removing.',
                                 read.id, article.id if article else u'`None`')
                    read.delete()
                    continue

                if extended_check:
                    try:
                        if read.subscriptions:

                            # TODO: remove this
                            #       check_set_subscriptions_131004_done
                            #       transient check.
                            if read.check_set_subscriptions_131004_done:
                                read.check_subscriptions()

                            else:
                                read.check_set_subscriptions_131004()
                                read.safe_reload()

                        else:
                            read.set_subscriptions()

                    except:
                        skipped_count += 1
                        LOGGER.exception(u'Could not set subscriptions on '
                                         u'read #%s, from article #%s, for '
                                         u'user #%s. Skipping.', read.id,
                                         article.id, read.user.id)
                        continue

                try:
                    if article.is_good:
                        changed_reads_count += 1

                        if verbose:
                            LOGGER.info(u'Bad read %s has a good article, '
                                        u'fixing…', read)

                        article.activate_reads(extended_check=extended_check)

                except:
                    LOGGER.exception(u'Could not activate reads from '
                                     u'article %s of read %s.',
                                     article, read)
                    if break_on_exception:
                        break

        finally:
            my_lock.release()

    LOGGER.info(u'global_reads_checker(): %s/%s reads processed '
                u'(%.2f%%), %s corrected (%.2f%%), %s deleted (%.2f%%), '
                u'%s skipped (%.2f%%).',
                processed_reads, total_reads_count,
                processed_reads * 100.0 / total_reads_count,
                changed_reads_count,
                changed_reads_count * 100.0 / processed_reads,
                wiped_reads_count,
                wiped_reads_count * 100.0 / processed_reads,
                skipped_count,
                skipped_count * 100.0 / processed_reads)


# ————————————————————————————————————————————— MongoDB to PostgreSQL migration

@task
def migrate_mongo_db_to_postgresql():

    config.FEED_FETCH_DISABLED = True

    mongofeeds = []

    for feed in mongofeeds:
        #clone feed into PG
        #for subscription in feed.subscriptions:
        #    clone subscription into PG
        pass

    # We need all feeds to be cloned at once, to speed up
    # articles re-linking in case of article in multiple feeds.

    config.FEED_FETCH_DISABLED = False

    for feed in mongofeeds:
        for article in feed.articles:
            #clone article into PG
            #(relink article to feeds)
            #for read in article.reads:
            #    clone reads into PG
            #    (relink read to subscriptions)
            pass


# ••••••••••••••••••••••••••••••••••••••••••••••••••• Move things to Archive DB


def archive_article_one_internal(article, counts):
    """ internal function. Do not use directly
        unless you know what you're doing. """

    delete_anyway = True
    article.switch_db('archive')

    try:
        article.save()

    except (NotUniqueError, DuplicateKeyError):
        counts['archived_dupes'] += 1

    except ValidationError:
        # If the article doesn't validate in the archive database, how
        # the hell did it make its way into the production one?? Perhaps
        # a scoria of the GR import which did update_one(set_*…), which
        # bypassed the validation phase.
        # Anyway, beiing here means the article is duplicate or orphaned.
        # So just forget the validation error and wipe it from production.
        LOGGER.exception(u'Article archiving failed for %s', article)
        counts['bad_articles'] += 1

    except:
        delete_anyway = False

    if delete_anyway:
        article.switch_db('default')
        article.delete()


@task(queue='clean')
def archive_articles(limit=None):

    counts = {
        'duplicates': 0,
        'orphaned': 0,
        'bad_articles': 0,
        'archived_dupes': 0,
    }

    if limit is None:
        limit = config.ARTICLE_ARCHIVE_BATCH_SIZE

    with no_dereference(Article) as ArticleOnly:
        if config.ARTICLE_ARCHIVE_OLDER_THAN > 0:
            older_than = now() - timedelta(
                days=config.ARTICLE_ARCHIVE_OLDER_THAN)

            duplicates = ArticleOnly.objects(
                duplicate_of__ne=None,
                date_published__lt=older_than).limit(limit)
            orphaned   = ArticleOnly.objects(
                orphaned=True,
                date_published__lt=older_than).limit(limit)

        else:
            duplicates = ArticleOnly.objects(duplicate_of__ne=None
                                             ).limit(limit)
            orphaned   = ArticleOnly.objects(orphaned=True).limit(limit)

    duplicates.no_cache()
    orphaned.no_cache()

    counts['duplicates'] = duplicates.count()
    counts['orphaned']   = orphaned.count()

    if counts['duplicates']:
        current = 0
        LOGGER.info(u'Archiving of %s duplicate article(s) started.',
                    counts['duplicates'])

        with benchmark('Archiving of %s duplicate article(s)'
                       % counts['duplicates']):
            for article in duplicates:
                archive_article_one_internal(article, counts)
                current += 1
                if current % 50 == 0:
                    LOGGER.info(u'Archived %s/%s duplicate articles so far.',
                                current, counts['duplicates'])

    if counts['orphaned']:
        current = 0
        LOGGER.info(u'Archiving of %s orphaned article(s) started.',
                    counts['orphaned'])

        with benchmark('Archiving of %s orphaned article(s)'
                       % counts['orphaned']):
            for article in orphaned:
                archive_article_one_internal(article, counts)
                current += 1
                if current % 50 == 0:
                    LOGGER.info(u'Archived %s/%s orphaned articles so far.',
                                current, counts['duplicates'])

    if counts['duplicates'] or counts['orphaned']:
        synchronize_statsd_articles_gauges(full=True)

        LOGGER.info('%s already archived and %s bad articles were found '
                    u'during the operation.', counts['archived_dupes'],
                    counts['bad_articles'])

    else:
        LOGGER.info(u'No article to archive.')


@task(queue='clean')
def archive_documents(limit=None, force=False):

    if config.DOCUMENTS_ARCHIVING_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'Document archiving disabled in configuration.')
        return

    # Be sure two archiving operations don't overlap, this is a very costly
    # operation for the database, and it can make the system very slugish.
    # The whole operation can be very long, we lock for a long time.
    my_lock = RedisExpiringLock('archive_documents', expire_time=3600 * 24)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'archive_documents() force unlock/re-acquire, '
                           u'be careful with that.')

        else:
            LOGGER.warning(u'archive_documents() is already locked, aborting.')
            return

    # these are tasks, but we run them sequentially in this global archive job
    # to avoid hammering the production database with multiple archive jobs.
    archive_articles(limit=limit)

    my_lock.release()
