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

import uuid
import logging

# from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save  # , pre_delete
from django.utils.translation import ugettext_lazy as _

from sparks.django.models import ModelDiffMixin

from oneflow.base.fields import IntRedisDescriptor
from oneflow.base.utils import register_task_method
from oneflow.base.utils.dateutils import (timedelta, today, combine,
                                          now, time)  # , make_aware, utc)

from common import DjangoUser as User

from folder import Folder
from feed import BaseFeed
from feed.mail import MailFeed
from tag import SimpleTag
from read import Read

LOGGER = logging.getLogger(__name__)

__all__ = [
    'Subscription',
    'subscribe_user_to_feed',

    # Make these accessible to compute them from `DocumentHelperMixin`.
    'subscription_all_articles_count_default',
    'subscription_unread_articles_count_default',
    'subscription_starred_articles_count_default',
    'subscription_archived_articles_count_default',
    'subscription_bookmarked_articles_count_default',

    # This one will be picked up by `Read` as an instance method.
    'generic_check_subscriptions_method',
]


# ————————————————————————————————————————————————————————————— Redis / Helpers

def get_subscription_thumbnail_upload_path(instance, filename):

    if not filename.strip():
        filename = uuid.uuid4()

    # The filename will be used in a shell command later. In case the
    # user/admin forgets the '"' in the configuration, avoid problems.
    filename = filename.replace(u' ', u'_')

    if instance:
        return 'subscription/{0}/thumbnails/{1}'.format(instance.id, filename)

    return u'thumbnails/%Y/%m/%d/{0}'.format(filename)


def subscription_all_articles_count_default(subscription):

    return subscription.reads.count()


def subscription_unread_articles_count_default(subscription):

    return subscription.reads.filter(is_read__ne=True).count()


def subscription_starred_articles_count_default(subscription):

    return subscription.reads.filter(is_starred=True).count()


def subscription_archived_articles_count_default(subscription):

    return subscription.reads.filter(is_archived=True).count()


def subscription_bookmarked_articles_count_default(subscription):

    return subscription.reads.filter(is_bookmarked=True).count()


# —————————————————————————————————————————————————————————————————————— Models

class ActiveSubscriptionsManager(models.Manager):
    def get_queryset(self):
        return super(ActiveSubscriptionsManager,
                     self).get_queryset().filter(feed__is_active=True)


class Subscription(ModelDiffMixin):

    """ Link users to feeds. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Subscription')
        verbose_name_plural = _(u'Subscriptions')
        unique_together = ('feed', 'user', )

    # ———————————————————————————————————————————————————————————————— Managers

    objects = models.Manager()
    active = ActiveSubscriptionsManager()

    # —————————————————————————————————————————————————————————————— Attributes

    feed = models.ForeignKey(BaseFeed)
    user = models.ForeignKey(User)

    items = models.ManyToManyField(Read, blank=True)

    # allow the user to rename the subscription in his/her selector
    name = models.CharField(verbose_name=_(u'Name'), max_length=255)

    tags = models.ManyToManyField(SimpleTag, blank=True,
                                  verbose_name=_(u'tags'))
    folders = models.ManyToManyField(Folder, blank=True,
                                     verbose_name=_(u'Folders'))

    notes = models.TextField(
        verbose_name=_(u'Notes'), null=True, blank=True,
        help_text=_(u'Write anything you want about this subscription. '
                    u'MultiMarkdown accepted.'))

    # Allow the user to also customize the visual of his/her subscription.
    thumbnail = models.ImageField(
        verbose_name=_(u'Thumbnail'), null=True, blank=True,
        upload_to=get_subscription_thumbnail_upload_path,
        help_text=_(u'Use either thumbnail when 1flow instance hosts the '
                    u'image, or thumbnail_url when hosted elsewhere. If '
                    u'both are filled, thumbnail takes precedence.'))

    thumbnail_url = models.URLField(
        verbose_name=_(u'Thumbnail URL'), null=True, blank=True,
        help_text=_(u'Full URL of the thumbnail displayed in the feed '
                    u'selector. Can be hosted outside of 1flow.'))

    # ———————————————————————————————————————————————————————— Redis attributes

    all_articles_count = IntRedisDescriptor(
        attr_name='s.aa_c', default=subscription_all_articles_count_default,
        set_default=True, min_value=0)

    unread_articles_count = IntRedisDescriptor(
        attr_name='s.ua_c', default=subscription_unread_articles_count_default,
        set_default=True, min_value=0)

    starred_articles_count = IntRedisDescriptor(
        attr_name='s.sa_c', default=subscription_starred_articles_count_default,
        set_default=True, min_value=0)

    archived_articles_count = IntRedisDescriptor(
        attr_name='s.ra_c',
        default=subscription_archived_articles_count_default,
        set_default=True, min_value=0)

    bookmarked_articles_count = IntRedisDescriptor(
        attr_name='s.ba_c',
        default=subscription_bookmarked_articles_count_default,
        set_default=True, min_value=0)

    # —————————————————————————————————————————————— Django / Python attributes

    def __unicode__(self):
        return _(u'{0}+{1} (#{2})').format(
            self.user.username, self.feed.name, self.id)

    @property
    def has_unread(self):

        # We need a boolean value for accurate template caching.
        return self.unread_articles_count != 0

    @property
    def is_active(self):

        return self.feed.is_active

    # ————————————————————————————————————————————————————————————————— Methods

    def mark_all_read(self, latest_displayed_read=None):

        if self.unread_articles_count == 0:
            return

        # count = self.unread_articles_count

        # self.unread_articles_count = 0

        # for folder in self.folders:
        #     folder.unread_articles_count -= count

        # self.user.unread_articles_count -= count

        # Marking all read is not a database-friendly operation,
        # thus it's run via a task to be able to return now immediately,
        # with cache numbers updated.
        #
        # HEADS UP: this task name will be registered later
        # by the register_task_method() call.
        subscription_mark_all_read_in_database_task.delay(
            self.id, now() if latest_displayed_read is None
            #
            # TRICK: we use self.user.reads for 2 reasons:
            #       - avoid importing `Read`, which would create a loop.
            #       - in case of a folder/global initiated mark_all_read(),
            #         the ID can be one of a read in another subscription
            #         and in this case, self.reads.get() will fail.
            #
            else latest_displayed_read.date_created)

    def mark_all_read_in_database(self, prior_datetime):
        """ Mark all reads as read.

        To avoid marking read the reads that could have been created
        between the task call and the moment it is effectively run,
        we define what to exactly mark as read with the datetime when
        the operation was done by the user.

        Also available as a task for background execution.

        .. note:: the archived reads stay archived, whatever their
            read status is. No need to test this attribute.

        .. todo:: implement ``until_datetime`` parameter, so that user
            can mark only the read he sees on the screen, or a period of time?
        """

        # We touch only unread. This avoid altering the auto_read attribute
        # on reads that have been manually marked read by the user.
        params = {'is_read__ne': True, 'date_created__lte': prior_datetime}

        if self.user.preferences.read.bookmarked_marks_unread:
            # Let bookmarked reads stay unread.
            params['is_bookmarked__ne'] = True

        impacted_unread = self.reads.filter(**params)
        impacted_count  = impacted_unread.count()

        impacted_unread.update(is_read=True,
                               is_auto_read=True,
                               date_read=prior_datetime,
                               date_auto_read=prior_datetime)

        # If our caches are correctly computed, doing
        # one more full query just for this is too much.
        #
        # self.compute_cached_descriptors(unread=True)

        self.unread_articles_count -= impacted_count

        for folder in self.folders:
            folder.unread_articles_count -= impacted_count

        self.user.unread_articles_count -= impacted_count

    def create_read(self, article, verbose=True, **kwargs):
        """ Returns a tuple (read, created) with the new (or existing) read,
            and ``created`` as a boolean indicating if it was actually created
            or if it existed before.

        """

        raise NotImplementedError('Review for relational database.')

        new_read = Read(article=article, user=self.user)

        try:
            new_read.save()

        except (NotUniqueError, DuplicateKeyError):
            if verbose:
                LOGGER.info(u'Duplicate read %s!', new_read)

            cur_read = Read.objects.get(article=article, user=self.user)

            # If another feed has already created the read, be sure the
            # current one is registered in the read via the subscriptions.
            cur_read.update(add_to_set__subscriptions=self)

            #
            # NOTE: we do not check `is_good` here, when the read was not
            #       created. This is handled (indirectly) via the article
            #       check part of Subscription.check_reads(). DRY.
            #

            return cur_read, False

        except:
            # We must not fail here, because often this method is called in
            # a loop 'for subscription in ….subscriptions:'. All other read
            # creations need to succeed.
            LOGGER.exception(u'Could not save read %s!', new_read)

        else:

            # XXX: todo remove this 'is not None', when database is clean…
            tags = [t for t in article.tags if t is not None]

            params = dict(('set__' + key, value)
                          for key, value in kwargs.items())

            # If the article was already there and fetched (mutualized from
            # another feed, for example), activate the read immediately.
            # If we don't do this here, the only alternative is the daily
            # global_reads_checker() task, which is not acceptable for
            # "just-added" subscriptions, whose reads are created via the
            # current method.
            if article.is_good:
                params['set__is_good'] = True

            new_read.update(set__tags=tags,
                            set__subscriptions=[self], **params)

            # Update cached descriptors
            self.all_articles_count += 1
            self.unread_articles_count += 1

            return new_read, True

    def check_reads(self, articles=None, force=False, extended_check=False):
        """ Also available as a task for background execution. """

        if not force:
            LOGGER.info(u'Subscription.check_reads() is very expensive and '
                        u'should be avoided in normal conditions. Call it '
                        u'with `force=True` if you are sure.')
            return

        raise Exception('REVIEW Subscription.check_reads()')

        yesterday = combine(today() - timedelta(days=1), time(0, 0, 0))
        is_older  = False
        my_now    = now()
        reads     = 0
        unreads   = 0
        failed    = 0
        missing   = 0
        rechecked = 0

        # See generic_check_subscriptions_method() for comment about this.
        if articles is None:
            articles = self.feed.good_articles.order_by('-date_published')

        for article in articles:
            #
            # NOTE: Checking `article.is_good()` is done at a lower
            #       level in the individual `self.create_read()`.
            #       It has nothing to do with the dates-only checks
            #       that we do here.
            #

            params = {}

            if is_older or article.date_published is None:
                params = {
                    'is_read':        True,
                    'is_auto_read':   True,
                    'date_read':      my_now,
                    'date_auto_read': my_now,
                }

            else:
                # As they are ordered by date, switching is_older to True will
                # avoid more date comparisons. MongoDB already did the job.
                if article.date_published < yesterday:

                    is_older = True

                    params = {
                        'is_read':        True,
                        'is_auto_read':   True,
                        'date_read':      my_now,
                        'date_auto_read': my_now,
                    }

                # implicit: else: pass
                # No params == all by default == is_read is False

            # The `create_read()` methods is defined
            # in `nonrel/read.py` to avoid an import loop.
            _, created = self.create_read(article, False, **params)

            if created:
                missing += 1

                if params.get('is_read', False):
                    reads += 1

                else:
                    unreads += 1

            elif created is False:
                rechecked += 1

                if extended_check:
                    try:
                        article.activate_reads()

                    except:
                        LOGGER.exception(u'Problem while activating reads '
                                         u'of Article #%s in Subscription '
                                         u'#%s.check_reads(), continuing '
                                         u'check.', article.id, self.id)

            else:
                failed += 1

        if missing or rechecked:
            #
            # TODO: don't recompute everything, just
            #    add or subscribe the changed counts.
            #
            self.compute_cached_descriptors(all=True, unread=True)

            for folder in self.folders:
                folder.compute_cached_descriptors(all=True, unread=True)

        LOGGER.info(u'Checked subscription #%s. '
                    u'%s/%s non-existing/re-checked, '
                    u'%s/%s read/unread and %s not created.',
                    self.id, missing, rechecked,
                    reads, unreads, failed)

        return missing, rechecked, reads, unreads, failed

# ———————————————————————————————————————————————————————————————— Celery tasks


register_task_method(Subscription, Subscription.mark_all_read_in_database,
                     globals())
register_task_method(Subscription, Subscription.check_reads, globals())


# ————————————————————————————————————————————————————————————————————— Signals


def subscription_pre_save(instance, **kwargs):
    """ Subscribe the mailfeed's owner if feed is beiing created. """

    subscription = instance

    if not subscription.pk:
        # The subscription is beeing created.
        return

    if isinstance(subscription.feed, MailFeed) \
            and 'name' in subscription.changed_fields:
        if subscription.user == subscription.feed.user:
            # The subscription's owner has changed the name
            # of a mailfeed he/she created, via the subscription
            # update interface. Synchronize it to the mail feed.
            #
            # HEADS UP: we use filter()/update()
            # to avoid a post_save() signal loop.
            #
            # HEADS UP: we use BaseFeed (and not
            # MailFeed) to avoid an import loop.
            BaseFeed.objects.filter(
                id=subscription.feed_id).update(name=subscription.name)

pre_save.connect(subscription_pre_save, sender=Subscription)


# ———————————————————————————————————————————————————————— Other models signals
# defined here either to avoid import loops, or
# because they depend on subscription features.

def mailfeed_post_save(instance, **kwargs):
    """ Subscribe the mailfeed's owner if feed is beiing created.

    When a user creates a mailfeed (obviously for him/her), we subscribe
    him/her automatically to this feed. This seems natural that he/she will
    except the Subscription to appear somewhere in the source selector.
    """

    if not kwargs.get('created', False):
        # The feed already exists, don't bother.
        return

    mailfeed = instance

    subscribe_user_to_feed(feed=mailfeed,
                           user=mailfeed.user,
                           background=True)


post_save.connect(mailfeed_post_save, sender=MailFeed)


# ————————————————————————————————————————————————————————————————————— Helpers


def subscribe_user_to_feed(user, feed, name=None,
                           force=False, background=False):
    """ Subscribe a user to a feed.

    This will create all reads (user+article) on the fly (or in the background).
    """

    subscription, created = Subscription.objects.get_or_create(
        user=user, feed=feed)

    if created:
        subscription.name = name or feed.name
        subscription.tags = feed.tags.all()

        subscription.save()

    if background:
        # HEADS UP: this task name will be registered later
        # by the register_task_method() call.
        #
        # 'True' is for the `force` argument.
        subscription_check_reads_task.delay(subscription.id, True)

    else:
        subscription.check_reads(force=True)

    LOGGER.info(u'Subscribed %s to %s via %s.', user, feed, subscription)

    return subscription


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def generic_check_subscriptions_method(self, commit=True, extended_check=False):
    """ For each subscription of current instance, check all reads.

    Eg see if subscribers have all the corresponding reads they should
    have, for all the articles of the subscription's feed or user.

    Also, wipe non-existing subscriptions (eg. dangling DBRefs).

    This method is used for `Feed` `User` classes (see later).

    When a user subscribes to a feed, it will be run to connect all
    existing articles to the user via new reads, avoiding the need
    for having two different method that basically accomplish the
    same thing.

    When checking subscriptions from their feed via this method,
    This will run the articles query once and will use the same
    QuerySet for all subscriptions to be checked.

    As is it a by-default-cached query, this will save some
    resources, at the expense of risking beiing declared
    “invalid cursor” at some point by the engine if checks take
    too much time.
    """

    raise NotImplementedError('Review for relational database.')

    # if not force:
    #     LOGGER.info(u'%s.check_subscriptions() is very costy and should '
    #                 u'not be needed in normal conditions. Call it with '
    #                 u'`force=True` if you are sure you want to run it.',
    #                 self.__class__.__name__)
    #     return

    to_keep       = []
    my_class_name = self.__class__.__name__

    for subscription in self.subscriptions:

        # TODO: code a not-hard-coded way to do this test,
        #       eg. get the values via class attributes?
        if my_class_name == 'Feed':
            attrs_to_test = [(subscription.user, 'User')]

        elif my_class_name == 'User':
            attrs_to_test = [(subscription.feed, 'Feed')]

        else:
            # We are a Read.
            attrs_to_test = [(subscription.user, 'User'),
                             (subscription.feed, 'Feed')]

        keep_it = True

        for attr_to_test, class_to_test in attrs_to_test:
            if isinstance(attr_to_test, DBRef) or attr_to_test is None:
                LOGGER.warning(u'Clearing Subscription #%s from %s #%s, it '
                               u'has a dangling reference to non-existing '
                               u'%s #%s.', subscription.id,
                               my_class_name, self.id, class_to_test,
                               attr_to_test.id if attr_to_test
                               else u'`None`')
                keep_it = False
                break

        if keep_it:
            to_keep.append(subscription)

    if len(to_keep) != self.subscriptions.count():
        self.subscriptions = to_keep

        if commit:
            self.save()
        # No need to update cached descriptors, they should already be ok…

    # avoid checking supbscriptions of a read, this will dead-loop if
    # Article.activate_reads(extended_check=True).
    if extended_check and my_class_name != 'Read':

        reads     = 0
        failed    = 0
        unreads   = 0
        missing   = 0
        rechecked = 0

        if my_class_name == 'Feed':
            articles = self.good_articles.order_by('-id')

        else:
            articles = None

        # Convert the subscriptions QuerySet to a list to avoid
        # "cursor #… not valid at server" on very long operations.
        subscriptions = [s for s in self.subscriptions]

        for subscription in subscriptions:
            try:
                smissing, srecheck, sreads, sunreads, sfailed = \
                    subscription.check_reads(articles, force=True,
                                             extended_check=True)
            except:
                # In case the subscription was unsubscribed during the
                # check operation, this is probably harmless.
                LOGGER.exception(u'Checking subscription #%s failed',
                                 subscription.id)

            else:
                reads     += sreads
                failed    += sfailed
                missing   += smissing
                unreads   += sunreads
                rechecked += srecheck

        LOGGER.info(u'Checked %s #%s with %s subscriptions%s. '
                    u'Totals: %s/%s non-existing/re-checked reads, '
                    u'%s/%s read/unread and %s not created.',
                    self.__class__.__name__, self.id,
                    self.subscriptions.count(),
                    u'' if articles is None
                    else (u' and %s articles' % articles.count()),
                    missing, rechecked, reads, unreads, failed)


BaseFeed.check_subscriptions = generic_check_subscriptions_method
User.check_subscriptions     = generic_check_subscriptions_method
Read.check_subscriptions     = generic_check_subscriptions_method
