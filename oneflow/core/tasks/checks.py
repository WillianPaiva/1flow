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

from celery import task, chain as tasks_chain

from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.core.mail import mail_managers
from django.utils.translation import ugettext_lazy as _

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.dateutils import (now, timedelta,
                                          naturaldelta, benchmark)

from ..models import (
    User,
    Article, BaseItem,
    Read,
    ARTICLE_ORPHANED_BASE,
    generate_orphaned_hash,
    DUPLICATE_STATUS,
    BaseFeed,
    UserFeeds,
    UserSubscriptions,
    UserCounters,
)

LOGGER = logging.getLogger(__name__)

from archive import archive_documents


@task(name='oneflow.core.tasks.global_checker_task', queue='check')
def global_checker_task(*args, **kwargs):
    """ Just run all tasks in a celery chain.

    This avoids them to overlap and hit the database too much.

    :param *args: ignored.
    :param *kwargs: ignored.
    """

    global_check_chain = tasks_chain(
        # HEADS UP: all subtasks are immutable, we just want them to run
        # chained to avoid dead times, without any link between them.

        # Begin by checking duplicates and orphans, archiving or deleting
        # them as much as we can. Next tasks will eventually benefit from
        # that by workin on smaller objects sets.
        global_duplicates_checker.si(),
        global_orphaned_checker.si(),
        archive_documents.si(),

        global_users_checker.si(),
        global_feeds_checker.si(),
        global_subscriptions_checker.si(),
        global_reads_checker.si(),
    )

    return global_check_chain.delay()


@task(name="oneflow.core.tasks.global_feeds_checker", queue='check')
def global_feeds_checker():
    """ Check all RSS feeds and their dependants. Close them if needed.

    No parameter.
    """

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
                        feed._meta.app_label,
                        feed._meta.module_name),
                        args=[feed.id]),

                    # Only RSS/Atom feeds have an URL…
                    feed.url if hasattr(feed, 'url') else '(NO URL)',

                    (u'closed on %s' % feed.date_closed)
                    if feed.date_closed
                    else u'(no closing date)',

                    feed.closed_reason or
                    u'none (or manually closed from the admin interface)',

                    feed.errors[0]
                    if len(feed.errors)
                    else u'(no error recorded)')

    def pretty_print_feed_list(feed_list):

        return '\n\n'.join(
            pretty_print_feed(feed)
            for feed in feed_list
        )

    dtnow         = now()
    limit_days    = config.FEED_CLOSED_WARN_LIMIT
    closed_limit  = dtnow - timedelta(days=limit_days)
    closed_tested = 0
    reopened_list = []

    # ———————————————————————————————— See if old closed feeds can be reopened.

    old_closed_feeds = BaseFeed.objects.filter(is_active=False).filter(
        date_closed__lt=closed_limit)

    for feed in old_closed_feeds:
        # check all closed feeds monthly, on their closing date anniversary.
        if feed.date_closed.day == dtnow.day:
            if feed.check_old_closed():
                reopened_list.append(feed)
            closed_tested += 1

    # ——————————————————————————————————————————— Report recently closed feeds.

    recently_closed_feeds = BaseFeed.objects.filter(is_active=False).filter(
        Q(date_closed=None) | Q(date_closed__gte=closed_limit))

    if not recently_closed_feeds.exists():
        LOGGER.info('No feed was closed in the last %s days, %s already '
                    u'closed checked for eventual back-to-life, of which '
                    u'%s were reopened.', limit_days, closed_tested,
                    len(reopened_list))
        return

    count = recently_closed_feeds.count()

    mail_managers(_(u'Reminder: {0} feed(s) closed in last '
                    u'{1} day(s), {2} automatically reopened').format(
                        count, limit_days, len(reopened_list)),
                  _(u"""
Here is the list, dates (if any), and reasons (if any) of closing:

{feed_list}

You can manually reopen any of them from the admin interface.

{closed_tested} closed feeds were tested to see if they came back to life,
out of which {reopened_count} were reopened:

{reopened_list}

""").format(
        feed_list=pretty_print_feed_list(recently_closed_feeds),
        closed_tested=closed_tested,
        reopened_count=len(reopened_list),
        reopened_list=pretty_print_feed_list(reopened_list)),
    )

    start_time = pytime.time()

    # Close the feeds, but after sending the mail,
    # So that initial reason is displayed at least
    # once to a real human.
    for feed in recently_closed_feeds:
        if feed.date_closed is None:
            feed.close('Automatic close by periodic checker task')

    LOGGER.info('Closed %s feeds in %s.', count,
                naturaldelta(pytime.time() - start_time))


@task(name="oneflow.core.tasks.global_subscriptions_checker", queue='check')
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

                # We check ALL feeds (including inactive ones) to be
                # sure all subscriptions / reads are up-to-date.
                feeds           = BaseFeed.objects.all()
                feeds_count     = feeds.count()
                processed_count = 0
                checked_count   = 0

                for feed in feeds.iterator():

                    if limit and checked_count > limit:
                        break

                    if extended_check:
                        feed.compute_cached_descriptors()
                        # all=True, good=True, bad=True

                    # Do not extended_check=True, this would double-do
                    # the subscription.check_reads() already called below.
                    feed.check_subscriptions()

                    for subscription in feed.subscriptions.all().iterator():

                        processed_count += 1

                        if subscription.all_items_count \
                                != feed.good_items_count:

                            checked_count += 1

                            LOGGER.info(u'Subscription %s (#%s) has %s reads '
                                        u'whereas its feed has %s good '
                                        u'articles; checking…',
                                        subscription.name, subscription.id,
                                        subscription.all_items_count,
                                        feed.good_items_count)

                            subscription.check_reads(
                                extended_check=extended_check, force=True)

                LOGGER.info(u'%s/%s (limit:%s) feeds processed, %s '
                            u'checked (%.2f%%).',
                            processed_count, feeds_count, limit,
                            checked_count, checked_count
                            * 100.0 / processed_count)

        if from_users:
            with benchmark("Check all subscriptions from users"):

                users           = User.objects.filter(is_active=True)
                users_count     = users.count()
                processed_count = 0

                for user in users:

                    # Do not extended_check=True, this would double-do
                    # the subscription.check_reads() already called below.
                    user.check_subscriptions()

                    if extended_check:
                        user.user_counters.compute_cached_descriptors()
                        # all=True, unread=True, starred=True, bookmarked=True

                        for subscription in user.subscriptions.all().iterator():
                                processed_count += 1

                                subscription.check_reads(extended_check=True,
                                                         force=True)

                LOGGER.info(u'%s users %sprocessed. '
                            u'All were checked.', users_count,
                            u'and %s subscriptions '.format(processed_count)
                            if extended_check else u'')

    finally:
        my_lock.release()


@task(name="oneflow.core.tasks.global_duplicates_checker", queue='check')
def global_duplicates_checker(limit=None, force=False):
    """ Check that duplicate articles have no more Reads anywhere.

    Fix it if not, and update all counters accordingly.

    :param limit: integer, the maximum number of duplicates to check.
        Default: none.
    :param force: boolean, default ``False``, allows to by bypass and
        reacquire the lock.
    """

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

    start_time = pytime.time()
    duplicates = BaseItem.objects.duplicate()

    total_dupes_count  = duplicates.count()
    total_reads_count  = 0
    processed_dupes    = 0
    done_dupes_count   = 0
    purged_dupes_count = 0

    purge_after_weeks_count = max(1, config.CHECK_DUPLICATES_PURGE_AFTER_WEEKS)
    purge_after_weeks_count = min(52, purge_after_weeks_count)

    purge_before_date = now() - timedelta(days=purge_after_weeks_count * 7)

    LOGGER.info(u'Done counting (took %s of pure SQL joy), starting procedure.',
                naturaldelta(pytime.time() - start_time))

    with benchmark(u"Check {0}/{1} duplicates".format(limit or u'all',
                   total_dupes_count)):

        try:
            for duplicate in duplicates.iterator():
                reads = duplicate.reads.all()

                processed_dupes += 1

                if reads.exists():
                    done_dupes_count  += 1
                    reads_count        = reads.count()
                    total_reads_count += reads_count

                    LOGGER.info(u'Duplicate %s #%s still has %s reads, fixing…',
                                duplicate._meta.model.__name__,
                                duplicate.id, reads_count)

                    duplicate.duplicate_of.register_duplicate(
                        duplicate, force=duplicate.duplicate_status
                        == DUPLICATE_STATUS.FINISHED)

                if duplicate.duplicate_status == DUPLICATE_STATUS.FINISHED:
                    #
                    # TODO: check we didn't get some race-conditions new
                    #       dependancies between the moment the duplicate
                    #       was marked duplicate and now.

                    if duplicate.date_created < purge_before_date:
                        try:
                            with transaction.atomic():
                                duplicate.delete()
                        except:
                            LOGGER.exception(u'Exception while deleting '
                                             u'duplicate %s #%s',
                                             duplicate._meta.model.__name__,
                                             duplicate.id)

                        purged_dupes_count += 1
                        LOGGER.info(u'Purged duplicate %s #%s from database.',
                                    duplicate._meta.model.__name__,
                                    duplicate.id)

                elif duplicate.duplicate_status in (
                    DUPLICATE_STATUS.NOT_REPLACED,
                        DUPLICATE_STATUS.FAILED):
                    # Something went wrong, perhaps the
                    # task was purged before beiing run.
                    duplicate.duplicate_of.register_duplicate(duplicate)
                    done_dupes_count += 1

                elif duplicate.duplicate_status is None:
                    # Something went very wrong. If the article is a known
                    # duplicate, its status field should have been set to
                    # at least NOT_REPLACED.
                    duplicate.duplicate_of.register_duplicate(duplicate)
                    done_dupes_count += 1

                    LOGGER.error(u'Corrected duplicate %s #%s found with no '
                                 u'status.', duplicate._meta.model.__name__,
                                 duplicate.id)

                if limit and processed_dupes >= limit:
                    break

        finally:
            my_lock.release()

    LOGGER.info(u'global_duplicates_checker(): %s/%s duplicates processed '
                u'(%.2f%%; limit: %s), %s corrected (%.2f%%), '
                u'%s purged (%.2f%%); %s reads altered.',

                processed_dupes, total_dupes_count,
                processed_dupes * 100.0 / total_dupes_count,

                limit or u'none',

                done_dupes_count,
                (done_dupes_count * 100.0 / processed_dupes)
                if processed_dupes else 0.0,

                purged_dupes_count,
                (purged_dupes_count * 100.0 / processed_dupes)
                if processed_dupes else 0.0,

                total_reads_count)


@task(name="oneflow.core.tasks.global_reads_checker", queue='check')
def global_reads_checker(limit=None, extended_check=False, force=False,
                         verbose=False, break_on_exception=False):
    """ Check all reads and their dependants.

    Will activate reads that are currently bad, but whose article is OK
    to display.

    This task is one of the most expensive thing in 1flow.
    It can run for hours because it scans all the bad reads and their
    articles, but will not kill the database with massive updates, it
    does them one by one.

    Can be disabled by ``config.CHECK_READS_DISABLED`` directive.

    :param limit: integer, the maximum number of duplicates to check.
        Default: none.
    :param extended_check: boolean, default ``False``.
        Runs :meth:`Read.set_subscriptions` if ``True`` and checked read
        has no subscription.
    :param force: boolean, default ``False``, allows to by bypass and
        reacquire the lock.
    :param verbose: boolean, default ``False``, display (more)
        informative messages.
    :param break_on_exception: boolean, default ``False``, stop processing
        at the first encountered exception. Whatever it is, the exception
        will be logged to sentry.
    """

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

    bad_reads = Read.objects.bad()

    total_reads_count   = bad_reads.count()
    processed_reads     = 0
    wiped_reads_count   = 0
    changed_reads_count = 0
    skipped_count       = 0

    with benchmark(u"Check {0}/{1} reads".format(limit or u'all',
                   total_reads_count)):
        try:
            for read in bad_reads.iterator():

                processed_reads += 1

                if limit and changed_reads_count >= limit:
                    break

                if read.is_good:
                    # This read has been activated via another
                    # checked one, attached to the same article.
                    changed_reads_count += 1
                    continue

                try:
                    article = read.item

                except:
                    LOGGER.critical(u'Could not get read.item for %s', read)
                    continue

                if extended_check:
                    try:
                        if read.subscriptions.all().exists():

                            # TODO: remove this
                            #       check_set_subscriptions_131004_done
                            #       transient check.
                            if read.check_set_subscriptions_131004_done:
                                read.check_subscriptions()

                            else:
                                read.check_set_subscriptions_131004()

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


def check_one_user(user, extended_check=False, force=False, verbose=False):
    u""" Completely check a user account and its “things”.

    Eg. user feeds, user subscriptions, user counters. Extended check:

    - recompute user counters (can be very long).

    :param extended_check: default ``False``, check more things.
    :param force: default ``False``, currently ignored.
    :param verbose: default ``False``, currently ignored.
    """

    try:
        user_feeds = user.user_feeds

    except:
        user_feeds = UserFeeds(user=user)
        user_feeds.save()

    user_feeds.check()

    try:
        user_subscriptions = user.user_subscriptions

    except:
        user_subscriptions = UserSubscriptions(user=user)
        user_subscriptions.save()

    user_subscriptions.check()

    try:
        user_counters = user.user_counters

    except:
        user_counters = UserCounters(user=user)
        user_counters.save()

    if extended_check:
        with benchmark(u'Recomputing cached descriptors'):
            user.user_counters.compute_cached_descriptors()


@task(name="oneflow.core.tasks.global_users_checker", queue='check')
def global_users_checker(limit=None, extended_check=False, force=False,
                         verbose=False, break_on_exception=False):
    """ Check all Users and their dependancies.

    Can be disabled by ``config.CHECK_USERS_DISABLED`` directive.

    :param limit: integer, the maximum number of users to check.
        Default: none.
    :param extended_check: boolean, default ``False``. Forwarded
        to :func:`check_one_user`.
    :param force: boolean, default ``False``, allows to by bypass and
        reacquire the lock.
    :param verbose: boolean, default ``False``. Forwarded
        to :func:`check_one_user`.
    :param break_on_exception: boolean, default ``False``, currently
        ignored in this function.
    """

    if config.CHECK_USERS_DISABLED:
        LOGGER.warning(u'Users check disabled in configuration.')
        return

    # This task runs twice a day. Acquire the lock for just a
    # little more time (13h, because Redis doesn't like floats)
    # to avoid over-parallelized runs.
    my_lock = RedisExpiringLock('check_all_users', expire_time=3600 * 13)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'Forcing users check…')

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'global_users_checker() is already '
                           u'locked, aborting.')
            return

    if limit is None:
        limit = 0

    active_users      = User.objects.filter(is_active=True)
    total_users_count = active_users.count()
    processed_users   = 0
    changed_users     = 0
    skipped_count     = 0

    with benchmark(u"Check {0}/{1} users".format(limit or u'all',
                   total_users_count)):
        try:
            for user in active_users.iterator():

                processed_users += 1

                if limit and changed_users >= limit:
                    break

                check_one_user(user, extended_check=extended_check,
                               force=force, verbose=verbose)

        finally:
            my_lock.release()

    LOGGER.info(u'global_users_checker(): %s/%s users processed '
                u'(%.2f%%), %s corrected (%.2f%%), %s skipped (%.2f%%).',
                processed_users, total_users_count,
                processed_users * 100.0 / total_users_count,
                changed_users,
                changed_users * 100.0 / processed_users,
                skipped_count,
                skipped_count * 100.0 / processed_users)


@task(name="oneflow.core.tasks.global_orphaned_checker", queue='check')
def global_orphaned_checker(limit=None, extended_check=False, force=False,
                            verbose=False, break_on_exception=False):
    """ Check all orphaned articles and delete them.

    They will be deleted only if they are duplicate of other orphaned ones,
    and only if the duplication replacement process finished successfully.
    If it failed, the orphan is left in place, to be able to re-run the
    operation later.

    Can be disabled by ``config.CHECK_ORPHANED_DISABLED`` directive.

    :param limit: integer, the maximum number of users to check.
        Default: none.
    :param extended_check: boolean, default ``False``. Forwarded
        to :func:`check_one_user`.
    :param force: boolean, default ``False``, allows to by bypass and
        reacquire the lock.
    :param verbose: boolean, default ``False``. Forwarded
        to :func:`check_one_user`.
    :param break_on_exception: boolean, default ``False``, currently
        ignored in this function.
    """

    if config.CHECK_ORPHANED_DISABLED:
        LOGGER.warning(u'Orphaned check disabled in configuration.')
        return

    # This task runs twice a day. Acquire the lock for just a
    # little more time (13h, because Redis doesn't like floats)
    # to avoid over-parallelized runs.
    my_lock = RedisExpiringLock('check_all_orphaned', expire_time=3600 * 13)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'Forcing orphaned check…')

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'global_orphaned_checker() is already '
                           u'locked, aborting.')
            return

    if limit is None:
        limit = 0

    orphaned_items       = Article.objects.orphaned().master()
    orphaned_items_count = orphaned_items.count()
    processed_orphans    = 0
    changed_orphans      = 0
    deleted_orphans      = 0
    skipped_orphans      = 0

    with benchmark(u"Check {0}/{1} orphans".format(limit or u'all',
                   orphaned_items_count)):
        try:
            for orphan in orphaned_items.iterator():
                processed_orphans += 1

                if limit and changed_orphans >= limit:
                    break

                old_url = orphan.url

                new_url = ARTICLE_ORPHANED_BASE + generate_orphaned_hash(
                    orphan.name, orphan.feeds.all())

                if new_url != old_url:
                    orphan.url = new_url
                    orphan.url_absolute = True

                else:
                    if not orphan.url_absolute:
                        changed_orphans += 1
                        orphan.url_absolute = True
                        orphan.save()

                    continue

                try:
                    orphan.save()

                except IntegrityError:
                    master = Article.objects.get(url=orphan.url)

                    # We have to put back the original URL, else the
                    # duplicate registration process will fail.
                    orphan.url = old_url

                    # Register the duplicate right here and now, to be able to
                    master.register_duplicate(orphan, force=force,
                                              background=False)

                    # Reload the orphan to get the refreshed duplicate status.
                    orphan = Article.objects.get(id=orphan.id)

                    if orphan.duplicate_status == DUPLICATE_STATUS.FINISHED:
                        orphan.delete()
                        deleted_orphans += 1

                        if verbose:
                            LOGGER.info(u'Deleted duplicate orphan %s', orphan)

                except:
                    skipped_orphans += 1
                    LOGGER.exception(u'Unhandled exception while checking %s',
                                     orphan)

                else:
                    changed_orphans += 1

        finally:
            my_lock.release()

    LOGGER.info(u'global_orphans_checker(): %s/%s orphans processed '
                u'(%.2f%%), %s corrected (%.2f%%), %s deleted (%.2f%%), '
                u'%s skipped (%.2f%%).',
                processed_orphans, orphaned_items_count,
                processed_orphans * 100.0 / orphaned_items_count,
                changed_orphans,
                changed_orphans * 100.0 / processed_orphans,
                deleted_orphans,
                deleted_orphans * 100.0 / processed_orphans,
                skipped_orphans,
                skipped_orphans * 100.0 / processed_orphans)
