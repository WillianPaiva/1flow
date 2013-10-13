# -*- coding: utf-8 -*-

import logging

from celery import task

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, CASCADE, PULL
from mongoengine.fields import (StringField, ListField, ReferenceField,
                                GenericReferenceField)
from mongoengine.errors import NotUniqueError

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from ....base.fields import IntRedisDescriptor
from ....base.utils.dateutils import (timedelta, today, combine,
                                      now, time)  # , make_aware, utc)

from .common import DocumentHelperMixin
from .folder import Folder
from .user import User
from .feed import Feed

LOGGER = logging.getLogger(__name__)


__all__ = ('subscription_post_create_task', 'Subscription', )


def subscription_all_articles_count_default(subscription):

    return subscription.reads.count()


def subscription_unread_articles_count_default(subscription):

    return subscription.reads.filter(is_read__ne=True).count()


def subscription_starred_articles_count_default(subscription):

    return subscription.reads.filter(is_starred=True).count()


def subscription_bookmarked_articles_count_default(subscription):

    return subscription.reads.filter(is_bookmarked=True).count()


@task(name='Subscription.post_create', queue='high')
def subscription_post_create_task(subscription_id, *args, **kwargs):

    subscription = Subscription.objects.get(id=subscription_id)
    return subscription.post_create_task(*args, **kwargs)


@task(name='Subscription.mark_all_read_in_database', queue='low')
def subscription_mark_all_read_in_database(subscription_id, *args, **kwargs):

    subscription = Subscription.objects.get(id=subscription_id)
    return subscription.mark_all_read_in_database(*args, **kwargs)


class Subscription(Document, DocumentHelperMixin):
    feed = ReferenceField('Feed', reverse_delete_rule=CASCADE)
    user = ReferenceField('User', unique_with='feed',
                          reverse_delete_rule=CASCADE)

    # allow the user to rename the field in its own subscription
    name = StringField(verbose_name=_(u'Name'))

    # TODO: convert to UserTag to use ReferenceField and reverse_delete_rule.
    tags = ListField(GenericReferenceField(),
                     default=list, verbose_name=_(u'Tags'),
                     help_text=_(u'Tags that will be applied to new reads in '
                                 u'this subscription.'))

    folders = ListField(ReferenceField(Folder, reverse_delete_rule=PULL),
                        verbose_name=_(u'Folders'), default=list,
                        help_text=_(u'Folders in which this subscription '
                                    u'appears (can be more than one).'))

    all_articles_count = IntRedisDescriptor(
        attr_name='s.aa_c', default=subscription_all_articles_count_default,
        set_default=True)

    unread_articles_count = IntRedisDescriptor(
        attr_name='s.ua_c', default=subscription_unread_articles_count_default,
        set_default=True)

    starred_articles_count = IntRedisDescriptor(
        attr_name='s.sa_c', default=subscription_starred_articles_count_default,
        set_default=True)

    bookmarked_articles_count = IntRedisDescriptor(
        attr_name='s.ba_c',
        default=subscription_bookmarked_articles_count_default,
        set_default=True)

    def pre_compute_cached_descriptors(self):

        # TODO: move this into the DocumentHelperMixin and detect all
        #       descriptors automatically by examining the __class__.

        self.all_articles_count = subscription_all_articles_count_default(self)
        self.unread_articles_count = \
            subscription_unread_articles_count_default(self)
        self.starred_articles_count = \
            subscription_starred_articles_count_default(self)
        self.bookmarked_articles_count = \
            subscription_bookmarked_articles_count_default(self)

    def __unicode__(self):
        return _(u'{0}+{1} (#{2})').format(
            self.user.username, self.feed.name, self.id)

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        subscription = document

        if created:
            if subscription._db_name != settings.MONGODB_NAME_ARCHIVE:
                subscription_post_create_task.delay(subscription.id)

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        self.name = self.feed.name

        self.save()

    @classmethod
    def subscribe_user_to_feed(cls, user, feed, force=False):

        try:
            sub = cls(user=user, feed=feed,
                      name=feed.name, tags=feed.tags).save()

        except (NotUniqueError, DuplicateKeyError):
            if not force:
                LOGGER.info(u'User %s already subscribed to feed %s.',
                            user, feed)
                return

        sub.check_reads(True)

        LOGGER.info(u'Subscribed %s to %s.', user, feed)

    def mark_all_read(self):

        if self.unread_articles_count == 0:
            return

        count = self.unread_articles_count
        self.unread_articles_count = 0

        for folder in self.folders:
            folder.unread_articles_count -= count

        # TODO: update global if no folders.

        # Marking all read is not a database-friendly operation,
        # thus it's run via a task to be able to return now immediately,
        # with cache numbers updated.
        subscription_mark_all_read_in_database.delay(self.id, now())

    def mark_all_read_in_database(self, prior_datetime):
        """ To avoid marking read the reads that could have been created
            between the task call and the moment it is effectively run,
            we define what to exactly mark as read with the datetime when
            the operation was done by the user.
        """

        currently_unread = self.reads.filter(is_read__ne=True,
                                             date_created__lt=prior_datetime)

        currently_unread.update(set__is_read=True,
                                set__date_read=prior_datetime)

    def check_reads(self, force=False, articles=None):

        if not force:
            LOGGER.info(u'This method is very costy and should not be needed '
                        u'in normal conditions, please call with `force=True` '
                        u'if you are really sure you want to run it.')
            return

        yesterday = combine(today() - timedelta(days=1), time(0, 0, 0))
        is_older  = False
        my_now    = now()
        reads     = 0
        unreads   = 0
        failed    = 0
        missing   = 0
        rechecked = 0

        # When checking the subscription from its feed, allow optimising
        # the whole story by not querying the articles again for each
        # subscription. The feed will do the query once, and forward the
        # QuerySet to all subscriptions to be checked.

        if articles is None:
            articles = self.feed.good_articles.order_by('-id')

        for article in articles:

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
                else:
                    # No params == all by default == is_read is False
                    pass

            created = self.create_reads(article, False, **params)

            if created:
                missing += 1

                if params.get('is_read', False):
                    reads += 1

                else:
                    unreads += 1

            elif created is False:
                rechecked += 1

            else:
                failed += 1

        if missing or rechecked:
            self.all_articles_count = \
                subscription_all_articles_count_default(self)
            self.unread_articles_count = \
                subscription_unread_articles_count_default(self)

            for folder in self.folders:
                folder.all_articles_count.compute_default()
                folder.unread_articles_count.compute_default()

        LOGGER.info(u'Checked subscription #%s. '
                    u'%s/%s non-existing/re-checked, '
                    u'%s/%s read/unread and %s not created.',
                    self.id, missing, rechecked,
                    reads, unreads, failed)

        return missing, rechecked, reads, unreads, failed


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def Feed_subscriptions_property_get(self):

    return Subscription.objects(feed=self)


def Folder_subscriptions_property_get(self):

    # No need to query on the user, it's already common to folder and
    # subscription. The "duplicate folder name" problem doesn't exist.
    return Subscription.objects(folders=self)


def User_subscriptions_property_get(self):
    return Subscription.objects(user=self)


def User_subscriptions_by_folder_property_get(self):

    subscriptions = Subscription.objects(user=self)
    by_folders    = {}

    for subscription in subscriptions:
        for folder in subscription.folders:
            if folder in by_folders:
                by_folders[folder].append(subscription)

            else:
                by_folders[folder] = [subscription]

    return by_folders


Folder.subscriptions          = property(Folder_subscriptions_property_get)
Feed.subscriptions            = property(Feed_subscriptions_property_get)
User.subscriptions            = property(User_subscriptions_property_get)
User.subscriptions_by_folder = property(
                                    User_subscriptions_by_folder_property_get)
