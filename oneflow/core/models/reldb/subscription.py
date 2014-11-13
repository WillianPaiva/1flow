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

from constance import config

# from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save, post_save  # , pre_delete
from django.utils.translation import ugettext_lazy as _

from sparks.foundations.classes import SimpleObject
from sparks.django.models import ModelDiffMixin

from oneflow.base.fields import IntRedisDescriptor
from oneflow.base.utils import register_task_method
from oneflow.base.utils.dateutils import (timedelta, today, combine,
                                          now, time)  # , make_aware, utc)

from common import DjangoUser as User

from tag import AbstractTaggedModel
from folder import Folder
from feed import BaseFeed
from feed.mail import MailFeed
from read import Read
from item import Article

LOGGER = logging.getLogger(__name__)

__all__ = [
    'Subscription',
    'subscribe_user_to_feed',
    'CheckReadsCounter',

    # Make these accessible to compute them from `DocumentHelperMixin`.
    'subscription_all_items_count_default',
    'subscription_unread_items_count_default',
    'subscription_starred_items_count_default',
    'subscription_archived_items_count_default',
    'subscription_bookmarked_items_count_default',

    # This one will be picked up by `Read` as an instance method.
    'generic_check_subscriptions_method',
]


def CheckReadsCounter():

    counters = SimpleObject()

    counters.reads = 0
    counters.unreads = 0
    counters.failed = 0
    counters.missing = 0
    counters.rechecked = 0

    return counters

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


def subscription_all_items_count_default(subscription):

    return subscription.reads.count()


def subscription_unread_items_count_default(subscription):

    return subscription.reads.filter(is_read=False).count()


def subscription_starred_items_count_default(subscription):

    return subscription.reads.filter(is_starred=True).count()


def subscription_archived_items_count_default(subscription):

    return subscription.reads.filter(is_archived=True).count()


def subscription_bookmarked_items_count_default(subscription):

    return subscription.reads.filter(is_bookmarked=True).count()


# —————————————————————————————————————————————————————————————————————— Models

class ActiveSubscriptionsManager(models.Manager):
    def get_queryset(self):
        return super(ActiveSubscriptionsManager,
                     self).get_queryset().filter(feed__is_active=True)


class Subscription(ModelDiffMixin, AbstractTaggedModel):

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

    feed = models.ForeignKey(BaseFeed, blank=True, related_name='subscriptions')
    user = models.ForeignKey(User, blank=True, related_name='all_subscriptions')

    reads = models.ManyToManyField(Read, blank=True, null=True,
                                   related_name='subscriptions')

    # allow the user to rename the subscription in his/her selector
    name = models.CharField(verbose_name=_(u'Name'),
                            max_length=255,
                            null=True, blank=True)

    folders = models.ManyToManyField(Folder, blank=True, null=True,
                                     verbose_name=_(u'Folders'),
                                     related_name='subscriptions')

    date_created = models.DateTimeField(auto_now_add=True, blank=True,
                                        verbose_name=_(u'Date created'))

    notes = models.TextField(
        verbose_name=_(u'Notes'), null=True, blank=True,
        help_text=_(u'Write anything you want about this subscription. '
                    u'MultiMarkdown accepted.'))

    # Allow the user to also customize the visual of his/her subscription.
    thumbnail = models.ImageField(
        verbose_name=_(u'Thumbnail'), null=True, blank=True,
        upload_to=get_subscription_thumbnail_upload_path, max_length=256,
        help_text=_(u'Use either thumbnail when 1flow instance hosts the '
                    u'image, or thumbnail_url when hosted elsewhere. If '
                    u'both are filled, thumbnail takes precedence.'))

    thumbnail_url = models.URLField(
        verbose_name=_(u'Thumbnail URL'), null=True, blank=True, max_length=384,
        help_text=_(u'Full URL of the thumbnail displayed in the feed '
                    u'selector. Can be hosted outside of 1flow.'))

    # ———————————————————————————————————————————————————————— Redis attributes

    all_items_count = IntRedisDescriptor(
        attr_name='s.aa_c', default=subscription_all_items_count_default,
        set_default=True, min_value=0)

    unread_items_count = IntRedisDescriptor(
        attr_name='s.ua_c', default=subscription_unread_items_count_default,
        set_default=True, min_value=0)

    starred_items_count = IntRedisDescriptor(
        attr_name='s.sa_c', default=subscription_starred_items_count_default,
        set_default=True, min_value=0)

    archived_items_count = IntRedisDescriptor(
        attr_name='s.ra_c',
        default=subscription_archived_items_count_default,
        set_default=True, min_value=0)

    bookmarked_items_count = IntRedisDescriptor(
        attr_name='s.ba_c',
        default=subscription_bookmarked_items_count_default,
        set_default=True, min_value=0)

    # —————————————————————————————————————————————— Django / Python attributes

    def __unicode__(self):
        return _(u'{0}+{1} (#{2})').format(
            self.user.username, self.feed.name, self.id)

    @property
    def has_unread(self):

        # We need a boolean value for accurate template caching.
        return self.unread_items_count != 0

    @property
    def is_active(self):

        return self.feed.is_active

    # ————————————————————————————————————————————————————————————————— Methods

    def compute_cached_descriptors(self, **kwargs):
        """ Do you guess? I guess yes. """

        self.all_items_count = \
            subscription_all_items_count_default(self)

        self.unread_items_count = \
            subscription_unread_items_count_default(self)

        self.starred_items_count = \
            subscription_starred_items_count_default(self)

        self.archived_items_count = \
            subscription_archived_items_count_default(self)

        self.bookmarked_items_count = \
            subscription_bookmarked_items_count_default(self)

    def mark_all_read(self, latest_displayed_read=None):

        if self.unread_items_count == 0:
            return

        # count = self.unread_items_count

        # self.unread_items_count = 0

        # for folder in self.folders:
        #     folder.unread_items_count -= count

        # self.user.unread_items_count -= count

        # Marking all read is not a database-friendly operation,
        # thus it's run via a task to be able to return now immediately,
        # with cache numbers updated.
        #
        # HEADS UP: this task name will be registered later
        # by the register_task_method() call.
        globals()['subscription_mark_all_read_in_database_task'].delay(
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
        params = {'is_read': False, 'date_created__lte': prior_datetime}

        if self.user.preferences.read.bookmarked_marks_unread:
            # Let bookmarked reads stay unread.
            params['is_bookmarked'] = False

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

        self.unread_items_count -= impacted_count

        for folder in self.folders.all():
            folder.unread_items_count -= impacted_count

        self.user.user_counters.unread_items_count -= impacted_count

    def create_read(self, item, verbose=True, **kwargs):
        """ Return a tuple (read, created) with the new (or existing) read.


        ``created`` is a boolean indicating if it was actually created
        or if it existed before.
        """

        read, created = Read.objects.get_or_create(item=item,
                                                   user=self.user)

        if created:
            read.subscriptions.add(self)
            read.tags.add(*item.tags.all())

            need_save = False

            for key, value in kwargs.items():
                setattr(read, key, value)
                need_save = True

            # If the item was already there and fetched (mutualized from
            # another feed, for example), activate the read immediately.
            # If we don't do this here, the only alternative is the daily
            # global_reads_checker() task, which is not acceptable for
            # "just-added" subscriptions, whose reads are created via the
            # current method.
            if item.is_good:
                read.is_good = True
                need_save = True

            if need_save:
                read.save()

            # Update cached descriptors
            self.all_items_count += 1
            self.unread_items_count += 1

            return read, True

        # If another feed has already created the read, be sure the
        # current one is registered in the read via the subscriptions.
        read.subscriptions.add(self)

        #
        # NOTE: we do not check `is_good` here, when the read was not
        #       created. This is handled (indirectly) via the item
        #       check part of Subscription.check_reads(). DRY.
        #

        return read, False

    def check_reads(self, items=None, force=False, extended_check=False):
        """ Also available as a task for background execution. """

        in_the_past = combine(today() - timedelta(
            days=config.SUBSCRIPTIONS_ITEMS_UNREAD_DAYS), time(0, 0, 0))

        my_now = now()

        counters = CheckReadsCounter()

        def create_read_for_item(item, params):

            _, created = self.create_read(item, verbose=False, **params)

            if created:
                counters.missing += 1

                if params.get('is_read', False):
                    counters.reads += 1

                else:
                    counters.unreads += 1

            elif created is False:
                counters.rechecked += 1

                if extended_check:
                    try:
                        item.activate_reads()

                    except:
                        LOGGER.exception(u'Problem while activating reads '
                                         u'of Article #%s in Subscription '
                                         u'#%s.check_reads(), continuing '
                                         u'check.', item.id, self.id)

            else:
                counters.failed += 1

        # ——————————————————————————————————————————————— First, check articles
        # We can order them by date and connect reads in the same order.

        if items is None:
            on_items = self.feed.good_items.instance_of(
                Article).order_by('Article___date_published')

        else:
            on_items = items.instance_of(
                Article).order_by('Article___date_published')

        for item in on_items.filter(Article___date_published__lt=in_the_past):

            # We reconnect the user to the whole feed history, but marking
            # old articles auto read, else there could be too much to read.
            create_read_for_item(item, {
                'is_read':        True,
                'is_auto_read':   True,
                'date_read':      my_now,
                'date_auto_read': my_now,
            })

        for item in on_items.filter(Q(Article___date_published__gte=in_the_past)
                                    | Q(Article___date_published=None)):

            # default parameters, reads will be unread.
            create_read_for_item(item, {})

        # ——————————————————————————————————————————————————— Then, other items
        # Do the same, but based on the date_created

        if items is None:
            on_items = self.feed.good_items.not_instance_of(Article)
        else:
            on_items = items.not_instance_of(Article)

        for item in on_items.filter(date_updated__lt=in_the_past):

            # We reconnect the user to the whole feed history, but marking
            # old items auto read, else there could be too much to read.
            create_read_for_item(item, {
                'is_read':        True,
                'is_auto_read':   True,
                'date_read':      my_now,
                'date_auto_read': my_now,
            })

        for item in on_items.filter(date_updated__gte=in_the_past):

            # default parameters, reads will be unread.
            create_read_for_item(item, {})

        for item in on_items:
            create_read_for_item(item, {})

        # —————————————————————————————————————————————————— Update descriptors

        if counters.missing or counters.rechecked:
            #
            # TODO: don't recompute everything, just
            #    add or subscribe the changed counts.
            #
            self.compute_cached_descriptors(all=True, unread=True)

            for folder in self.folders.all():
                folder.compute_cached_descriptors(all=True, unread=True)

        LOGGER.info(u'Checked subscription #%s. '
                    u'%s/%s non-existing/re-checked, '
                    u'%s/%s read/unread and %s not created.',
                    self.id, counters.missing, counters.rechecked,
                    counters.reads, counters.unreads, counters.failed)

        return counters

# ———————————————————————————————————————————————————————————————— Celery tasks


register_task_method(Subscription, Subscription.mark_all_read_in_database,
                     globals(), queue=u'background')
register_task_method(Subscription, Subscription.check_reads,
                     globals(), queue=u'check')


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
        globals()['subscription_check_reads_task'].apply_async(
            args=(subscription.id,),
            kwargs={'force': True}
        )

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

    # if not force:
    #     LOGGER.info(u'%s.check_subscriptions() is very costy and should '
    #                 u'not be needed in normal conditions. Call it with '
    #                 u'`force=True` if you are sure you want to run it.',
    #                 self.__class__.__name__)
    #     return

    my_class_name = self.__class__.__name__

    # avoid checking supbscriptions of a read, this will dead-loop if
    # Article.activate_reads(extended_check=True).
    if extended_check and my_class_name != 'Read':

        counters = CheckReadsCounter()

        if my_class_name == 'Feed':
            articles = self.good_items.order_by('-id')

        else:
            articles = None

        # Convert the subscriptions QuerySet to a list to avoid
        # "cursor #… not valid at server" on very long operations.
        subscriptions = [s for s in self.subscriptions.all()]

        for subscription in subscriptions:
            try:
                scounters = subscription.check_reads(articles, force=True,
                                                     extended_check=True)
            except:
                # In case the subscription was unsubscribed during the
                # check operation, this is probably harmless.
                LOGGER.exception(u'Checking subscription #%s failed',
                                 subscription.id)

            else:
                counters.reads     += scounters.reads
                counters.failed    += scounters.failed
                counters.missing   += scounters.missing
                counters.unreads   += scounters.unreads
                counters.rechecked += scounters.rechecked

        LOGGER.info(u'Checked %s #%s with %s subscriptions%s. '
                    u'Totals: %s/%s non-existing/re-checked reads, '
                    u'%s/%s read/unread and %s not created.',
                    self.__class__.__name__, self.id,
                    self.subscriptions.count(),
                    u'' if articles is None
                    else (u' and %s articles' % articles.count()),
                    counters.missing, counters.rechecked, counters.reads,
                    counters.unreads, counters.failed)


def Read_set_subscriptions_method(self, commit=True):
    """ Set a read subscriptions from scratch.

    In fact, from intersecting the feeds of the user and the articles.
    """

    # @all_subscriptions, because here internal feeds count.
    all_user_feeds_ids = [subscription.feed_id for subscription
                          in self.user.all_subscriptions.all()]

    article_feeds = self.item.feeds.filter(id__in=all_user_feeds_ids)

    # clearing allows to remove dangling subscriptions.
    #
    # HEADS UP/ TODO: isn't that already handled by the CASCADE mechanism
    #                 of the DB engine??? I'm too familiar with MongoDB
    #                 that let us developers handle all the dirty work.
    #
    self.subscriptions.clear()

    # HEADS UP: searching only for feed__in=article_feeds will lead
    # to have other user's subscriptions attached to the read.
    # Harmless but very confusing.
    self.subscriptions.add(*Subscription.objects.filter(
                           feed__in=article_feeds,
                           user=self.user))

    # if commit:
    #    self.save()
    #    TODO: only for the new subscriptions.
    #    self.update_cached_descriptors( … )

    return self.subscriptions.all()


def User_subscriptions_property_get(self):
    """ “Normal” subscriptions, eg. not special (immutable) ones. """

    # Add all special subscriptions here.
    return self.all_subscriptions.exclude(
        id__in=self.user_subscriptions.all_ids
    )


def User_open_subscriptions_property_get(self):

    # NOTE: self.subscriptions is defined
    # in nonrel.subscription to avoid import loop.
    return self.subscriptions.filter(feed__is_active=True)


def User_closed_subscriptions_property_get(self):

    # NOTE: self.subscriptions is defined
    # in nonrel.subscription to avoid import loop.
    return self.subscriptions.filter(feed__is_active=False)


def User_nofolder_subscriptions_property_get(self):

    return self.subscriptions.filter(
        # NOTE: feed__is_internal=False would lead to NOT get subscriptions
        #       to other users special feeds (eg. Karmak23 will not get his
        #       own subscription to mchaignot's written_items)
        folders=None
    )


def User_nofolder_open_subscriptions_property_get(self):

    return self.nofolder_subscriptions.filter(feed__is_active=True)


def User_nofolder_closed_subscriptions_property_get(self):

    return self.nofolder_subscriptions.filter(feed__is_active=False)


def User_subscriptions_by_folder_property_get(self):
    """ Return a dict of subscriptions, keyed by folder. """

    by_folders = {}

    for subscription in self.subscriptions.all():
        for folder in subscription.folders.all():
            if folder in by_folders:
                by_folders[folder].append(subscription)

            else:
                by_folders[folder] = [subscription]

    return by_folders


def Folder_open_subscriptions_property_get(self):

    # No need to query on the user, it's already common to folder and
    # subscription. The "duplicate folder name" problem doesn't exist.
    return self.subscriptions.filter(feed__is_active=True)


User.subscriptions = property(User_subscriptions_property_get)
User.open_subscriptions = property(User_open_subscriptions_property_get)
User.closed_subscriptions = property(User_closed_subscriptions_property_get)
User.nofolder_subscriptions = property(
    User_nofolder_subscriptions_property_get)
User.nofolder_open_subscriptions = property(
    User_nofolder_open_subscriptions_property_get)
User.nofolder_closed_subscriptions = property(
    User_nofolder_closed_subscriptions_property_get)
User.subscriptions_by_folder = property(
    User_subscriptions_by_folder_property_get)

BaseFeed.check_subscriptions = generic_check_subscriptions_method
User.check_subscriptions     = generic_check_subscriptions_method
Read.check_subscriptions     = generic_check_subscriptions_method
Read.set_subscriptions       = Read_set_subscriptions_method

Folder.open_subscriptions = property(Folder_open_subscriptions_property_get)
