# -*- coding: utf-8 -*-
"""
Copyright 2014 Olivier Cortès <oc@1flow.io>.

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
import six
import json
import uuid
import logging

from statsd import statsd
from constance import config
from collections import OrderedDict
from transmeta import TransMeta

from json_field import JSONField

# from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save, pre_save  # , pre_delete

from polymorphic.base import PolymorphicModelBase
from polymorphic import (
    PolymorphicQuerySet,
    PolymorphicManager,
    PolymorphicModel,
)
from sparks.django.models.mixins import DiffMixin

from oneflow.base.fields import IntRedisDescriptor, DatetimeRedisDescriptor
from oneflow.base.utils.dateutils import now, timedelta, today

from oneflow.base.utils import (
    register_task_method,
    RedisExpiringLock,
)

from ..common import (
    DjangoUser as User,
    # REDIS,
    CONTENT_TYPES,
    ORIGINS,
    # BAD_SITE_URL_BASE,
)

from ..duplicate import AbstractDuplicateAwareModel
from ..tag import AbstractTaggedModel
from ..language import AbstractMultipleLanguagesModel
from ..item import BaseItem, Article, Tweet
# from ..tag import SimpleTag

from common import throttle_fetch_interval

LOGGER = logging.getLogger(__name__)

__all__ = [
    'BaseFeed',
    'BaseFeedMeta',
    'BaseFeedManager',
    'BaseFeedQuerySet',
    'basefeed_pre_save',

    'basefeed_all_items_count_default',
    'basefeed_good_items_count_default',
    'basefeed_bad_items_count_default',
    'basefeed_recent_items_count_default',
    'basefeed_subscriptions_count_default',
]


# ————————————————————————————————————————— Utils / redis descriptors functions


def get_feed_thumbnail_upload_path(instance, filename):

    if not filename.strip():
        filename = uuid.uuid4()

    # The filename will be used in a shell command later. In case the
    # user/admin forgets the '"' in the configuration, avoid problems.
    filename = filename.replace(u' ', u'_')

    if instance:
        return 'feed/{0}/thumbnails/{1}'.format(instance.id, filename)

    return u'thumbnails/%Y/%m/%d/{0}'.format(filename)


def basefeed_all_items_count_default(feed, *args, **kwargs):

    return feed.items.count()


def basefeed_good_items_count_default(feed, *args, **kwargs):

    return feed.good_items.count()


def basefeed_bad_items_count_default(feed, *args, **kwargs):

    return feed.bad_items.count()


def basefeed_recent_items_count_default(feed, *args, **kwargs):

    return feed.recent_items.count()


def basefeed_subscriptions_count_default(feed, *args, **kwargs):

    return feed.subscriptions.count()


# ———————————————————————————————————————————————————————————————————— Managers


class BaseFeedQuerySet(PolymorphicQuerySet):

    """ Feed based queryset.

    .. note:: this query set will be patched by subclasses.
    """

    def inactive(self):
        return self.filter(is_active=False)

    def active(self):
        return self.filter(is_active=True)

    def internal(self):
        return self.filter(is_internal=True)

    def external(self):
        return self.filter(is_internal=False)

    def master(self):
        return self.filter(duplicate_of_id=None)

    def good(self):
        return self.master().active().external().filter(is_good=True)


class BaseFeedManager(PolymorphicManager):

    """ A manager that adds some things. """

    use_for_related_fields = True
    queryset_class = BaseFeedQuerySet


# ——————————————————————————————————————————————————————————————————————— Model


class BaseFeedMeta(PolymorphicModelBase, TransMeta):

    """ Wow. This one was difficult to craft. """

    pass


class BaseFeed(six.with_metaclass(BaseFeedMeta,
                                  PolymorphicModel,
                                  AbstractDuplicateAwareModel,
                                  AbstractMultipleLanguagesModel,
                                  AbstractTaggedModel,
                                  DiffMixin)):

    """ Base 1flow feed.

    .. todo::
        date_added   → date_created
        created_by   → user
        restricted   → is_restricted
        closed       → is_active
        last_fetch   → date_last_fetch
        good_for_use → is_good
        errors : ListField(StringField) → JSONField
    """

    # This should be overriden by subclasses if needed.
    REFRESH_LOCK_INTERVAL = None

    # By default, feeds continue to be fetched,
    # even if no user is subscribed to them.
    AUTO_CLOSE_WHEN_NO_SUBSCRIPTION_LEFT = False

    class Meta:
        app_label = 'core'
        translate = ('short_description', 'description', )
        verbose_name = _(u'Base feed')
        verbose_name_plural = _(u'Base feeds')

    INPLACEEDIT_EXCLUDE = ('errors', 'options', )

    # ———————————————————————————————————————————————————————————————— Managers

    objects = BaseFeedManager()

    #
    # BIG HEADS UP: for an unknown reason, if I define both managers, Django
    #               picks the `good` as the default one, which is not what we
    #               want at all, and goes against the documentation which says
    #               the first defined will be the default one. Thus for now,
    #               both are deactivated and we use only one, that offers
    #               multiple filters at the QuerySet level.
    #
    # add the default polymorphic manager first
    # objects = models.Manager()
    # objects = PolymorphicManager()
    # good_feeds = GoodFeedsManager()

    # —————————————————————————————————————————————————————————————— Attributes

    # NOTE: keep ID a simple integer/auto
    # field, this surely helps JOIN operations.
    # id             = models.UUIDField(primary_key=True,
    #                                   default=uuid.uuid4, editable=False)

    # We use `.user` attribute name for writing-easyness of permissions classes,
    # But really the `.user` attribute has different roles. Please always refer
    # to its verbose_name to exactly know what it is really.
    user = models.ForeignKey(User,
                             null=True, blank=True,
                             verbose_name=_(u'Creator'),
                             related_name='feeds')

    name = models.CharField(verbose_name=_(u'name'),
                            null=True, blank=True,
                            max_length=255)

    slug = models.CharField(verbose_name=_(u'slug'),
                            max_length=255,
                            null=True, blank=True)

    items = models.ManyToManyField(BaseItem, blank=True, null=True,
                                   verbose_name=_(u'Feed items'),
                                   related_name='feeds')

    date_created = models.DateTimeField(auto_now_add=True, blank=True,
                                        verbose_name=_(u'Date created'))

    is_internal = models.BooleanField(verbose_name=_(u'Internal'),
                                      blank=True, default=False)

    is_restricted  = models.BooleanField(
        default=False, verbose_name=_(u'restricted'), blank=True,
        help_text=_(u'Is this feed available only to paid subscribers on its '
                    u'publisher\'s web site?'))

    is_active = models.BooleanField(
        verbose_name=_(u'active'), default=True, blank=True,
        help_text=_(u'Is the feed refreshed or dead?'))

    date_closed = models.DateTimeField(verbose_name=_(u'date closed'),
                                       null=True, blank=True)

    closed_reason = models.TextField(verbose_name=_(u'closed reason'),
                                     null=True, blank=True)

    fetch_interval = models.IntegerField(
        default=config.FEED_FETCH_DEFAULT_INTERVAL,
        verbose_name=_(u'fetch interval'), blank=True)

    date_last_fetch = models.DateTimeField(verbose_name=_(u'last fetch'),
                                           null=True, blank=True, db_index=True)

    errors = JSONField(default=list, blank=True)
    options = JSONField(default=dict, blank=True)

    notes = models.TextField(
        verbose_name=_(u'Notes'), null=True, blank=True,
        help_text=_(u'Internal notes for 1flow staff related to this feed.'))

    is_good = models.BooleanField(
        verbose_name=_(u'Shown in selector'),
        default=False, db_index=True,
        help_text=_(u'Make this feed available to new subscribers in the '
                    u'selector wizard. Without this, the user can still '
                    u'subscribe but he must know it and manually enter '
                    u'the feed address.'))

    thumbnail = models.ImageField(
        verbose_name=_(u'Thumbnail'), null=True, blank=True,
        upload_to=get_feed_thumbnail_upload_path, max_length=256,
        help_text=_(u'Use either thumbnail when 1flow instance hosts the '
                    u'image, or thumbnail_url when hosted elsewhere. If '
                    u'both are filled, thumbnail takes precedence.'))

    thumbnail_url = models.URLField(
        verbose_name=_(u'Thumbnail URL'), null=True, blank=True, max_length=384,
        help_text=_(u'Full URL of the thumbnail displayed in the feed '
                    u'selector. Can be hosted outside of 1flow.'))

    short_description = models.CharField(
        null=True, blank=True,
        max_length=256, verbose_name=_(u'Short description'),
        help_text=_(u'Public short description of the feed, for '
                    u'auto-completer listing. Markdown text.'))

    description = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Description'),
        help_text=_(u'Public description of the feed. Markdown text.'))

    # ——————————————————————————————————————————— Cached descriptors & updaters

    # TODO: create an abstract class that will allow to not specify
    #       the attr_name here, but make it automatically created.
    #       This is an underlying implementation detail and doesn't
    #       belong here.
    latest_item_date_published = DatetimeRedisDescriptor(
        # 5 years ealier should suffice to get old posts when starting import.
        attr_name='bf.la_dp', default=now() - timedelta(days=1826))

    all_items_count = IntRedisDescriptor(
        attr_name='bf.ai_c', default=basefeed_all_items_count_default,
        set_default=True, min_value=0)

    good_items_count = IntRedisDescriptor(
        attr_name='bf.gi_c', default=basefeed_good_items_count_default,
        set_default=True, min_value=0)

    bad_items_count = IntRedisDescriptor(
        attr_name='bf.bi_c', default=basefeed_bad_items_count_default,
        set_default=True, min_value=0)

    recent_items_count = IntRedisDescriptor(
        attr_name='bf.ri_c', default=basefeed_recent_items_count_default,
        set_default=True, min_value=0)

    subscriptions_count = IntRedisDescriptor(
        attr_name='bf.s_c', default=basefeed_subscriptions_count_default,
        set_default=True, min_value=0)

    def update_latest_item_date_published(self):
        """ This seems simple, but this operations costs a lot. """

        try:
            # This query should still cost less than the pure and bare
            # `self.latest_article.date_published` which will first sort
            # all articles of the feed before getting the first of them.
            self.latest_item_date_published = self.recent_items.order_by(
                '-date_published').first().date_published
        except:
            # Don't worry, the default value of
            # the descriptor should fill the gaps.
            pass

    def update_all_items_count(self):

        self.all_items_count = basefeed_all_items_count_default(self)

    def update_good_items_count(self):

        self.good_items_count = basefeed_good_items_count_default(self)

    def update_bad_items_count(self):

        self.bad_items_count = basefeed_bad_items_count_default(self)

    def update_subscriptions_count(self):

        self.subscriptions_count = basefeed_subscriptions_count_default(self)

    def update_recent_items_count(self, force=False):
        """ This task is protected to run only once per day,
            even if is called more. """

        urac_lock = RedisExpiringLock(self, lock_name='urac', expire_time=86100)

        if urac_lock.acquire() or force:
            self.recent_items_count = self.recent_items.count()

        elif not force:
            LOGGER.warning(u'No more than one update_recent_items_count '
                           u'per day (feed %s).', self)
        #
        # Don't bother release the lock, this will
        # ensure we are not called until tomorrow.
        #

    def compute_cached_descriptors(self):

        self.update_all_items_count()
        self.update_good_items_count()
        self.update_bad_items_count()
        self.update_subscriptions_count()
        self.update_recent_items_count()

        # This one costs a lot.
        # self.update_latest_item_date_published()

    # ————————————————————————————————————————————————————— Articles properties

    @property
    def recent_items(self):
        return self.good_items.filter(
            date_published__gt=today()
            - timedelta(
                days=config.FEED_ADMIN_MEANINGFUL_DELTA))

    @property
    def native_items(self):
        """ Return items whose model is related to the feed model.

        This method is meant to be overriden by polymorphic inherited models.
        """

        return self.items.all()

    @property
    def good_items(self):
        """ Subscriptions should always use :attr:`good_items` to give
            to users only useful content for them, whereas :class:`Feed`
            will use :attr:`articles` or :attr:`all_items` to reflect
            real numbers.
        """

        #
        # NOTE: sync the conditions with @Article.is_good
        #       and invert them in @BaseFeed.bad_items
        #

        return self.items.filter(duplicate_of=None) \
            & self.items.instance_of(Article).filter(
                Article___url_absolute=True) \
            | self.items.not_instance_of(Article)

    @property
    def bad_items(self):

        #
        # NOTE: invert these conditions in @Feed.good_items
        #

        return self.items.filter(Q(Article___url_absolute=False)
                                 | ~Q(duplicate_of_id=None))

    # NOTE for myself: these property & method are provided by Django
    #       bye-bye MongoDB glue code everywhere to mimic relational DB.
    #
    # @property
    # def articles(self):
    #     """ A simple version of :meth:`get_items`. """
    #     return Article.objects(feeds__contains=self)
    #
    # def get_items(self, limit=None):
    #     """ A parameter-able version of the :attr:`articles` property. """
    #
    #     if limit:
    #         return self.items.order_by('-date_published').limit(limit)
    #
    #     return self.items.order_by('-date_published')

    # —————————————————————————————————————————————————————— Django & Grappelli

    def __unicode__(self):
        """ Hello, pep257. I love you so. """

        return _(u'BaseFeed {0} (#{1})').format(self.name, self.id)

    @staticmethod
    def autocomplete_search_fields():
        """ grappelli auto-complete method. """

        return ('name__icontains', )

    @property
    def refresh_lock(self):
        try:
            return self.__refresh_lock

        except AttributeError:
            self.__refresh_lock = RedisExpiringLock(
                self, lock_name='fetch',
                expire_time=self.REFRESH_LOCK_INTERVAL or self.fetch_interval
            )
            return self.__refresh_lock

    # —————————————————————————————————————————————————————————— Internal utils

    def has_option(self, option):
        """ True if option in self.options. """

        return option in self.options

    def reopen(self, commit=True):
        """ Reopen the feed, clearing errors, date closed, etc. """

        self.errors        = []
        self.is_active     = True
        self.date_closed   = now()
        self.closed_reason = u'Reopen on %s' % now().isoformat()
        self.save()

        statsd.gauge('feeds.counts.open', 1, delta=True)

        LOGGER.info(u'Feed %s has just been re-opened.', self)

    def close(self, reason=None, commit=True):
        """ Close the feed with or without a reason. """

        self.is_active = False
        self.date_closed = now()
        self.closed_reason = reason or _(u'NO REASON GIVEN')

        if commit:
            self.save()

        statsd.gauge('feeds.counts.open', -1, delta=True)

        LOGGER.warning(u'Feed %s closed with reason "%s"!',
                       self, self.closed_reason)

    def error(self, message, commit=True, last_fetch=False):
        """ Take note of an error.

        If the maximum number of errors is reached, close the feed and
        return ``True``; else just return ``False``.

        :param last_fetch: as a commodity, set this to ``True`` if you
            want this method to update the :attr:`last_fetch` attribute
            with the value of ``now()`` (UTC). Default: ``False``.

        :param commit: as in any other Django DB-related method, set
            this to ``False`` if you don't want this method to call
            ``self.save()``. Default: ``True``.
        """

        LOGGER.error(u'Error on feed %s: %s.', self, message)

        error_message = u'{0} @@{1}'.format(message,
                                            now().isoformat())

        # Put the errors more recent first.
        self.errors.insert(0, error_message)

        if last_fetch:
            self.date_last_fetch = now()

        retval = False

        if len(self.errors) >= config.FEED_FETCH_MAX_ERRORS:
            if self.is_active:
                self.close(u'Too many errors on the feed. Last was: %s'
                           % self.errors[0], commit=False)

                # LOGGER.critical(u'Too many errors on feed %s, closed.', self)

            # Keep only the most recent errors.
            self.errors = self.errors[:config.FEED_FETCH_MAX_ERRORS]

            retval = True

        if commit:
            self.save()

        statsd.incr('feeds.refresh.global.errors')

        return retval

    # —————————————————————————————————————————————————————— High-level methods

    def refresh_must_abort(self, force=False, commit=True):
        """ Returns ``True`` if one or more abort conditions is met.
            Checks the feed cache lock, the ``last_fetch`` date, etc.
        """

        if not self.is_active:
            LOGGER.info(u'Feed %s is closed. refresh aborted.', self)
            return True

        if self.is_internal:
            LOGGER.info(u'Feed %s is internal, no need to refresh.', self)
            return True

        if config.FEED_FETCH_DISABLED:
            # we do not raise .retry() because the global refresh
            # task will call us again anyway at next global check.
            LOGGER.info(u'Feed %s refresh disabled by configuration.', self)
            return True

        try:
            if self.refresh_must_abort_internal():
                return True

        except AttributeError:
            pass

        # ————————————————————————————————————————————————  Try to acquire lock

        if not self.refresh_lock.acquire():
            if force:
                LOGGER.warning(u'Forcing refresh for feed %s, despite of '
                               u'lock already acquired.', self)
                self.refresh_lock.release()
                self.refresh_lock.acquire()

            else:
                LOGGER.info(u'Refresh for %s already running, aborting.', self)
                return True

        if self.date_last_fetch is not None and self.date_last_fetch >= (
                now() - timedelta(seconds=self.fetch_interval)):
            if force:
                LOGGER.warning(u'Forcing refresh of recently fetched feed %s.',
                               self)
            else:
                LOGGER.info(u'Last refresh of feed %s too recent, aborting.',
                            self)
                return True

        return False

    def refresh(self, force=False):
        """ Look for new content in a 1flow feed. """

        # HEADS UP: refresh_must_abort() has already acquire()'d our lock.
        if self.refresh_must_abort(force=force):
            self.refresh_lock.release()
            return

        preventive_slow_down = False

        try:
            data = self.refresh_feed_internal(force=force)

        except:
            LOGGER.exception(u'Could not refresh feed %s, operating '
                             u'preventive slowdown.', self)
            preventive_slow_down = True

        else:
            if data is None:
                # An error occured and has already been stored. The feed
                # has eventually already been closed if too many errors.
                # In case it's still open, slow down things.
                preventive_slow_down = True

            elif data is True:
                # The feed is handling its internals on his own behalf.
                # Eg. a Twitter feed will tweak self.last_fetch anyhow
                # it needs to prevent quota overflows. Just let it go.
                return

        if preventive_slow_down:
            # do not the queue be overflowed by refresh_all_feeds()
            # checking this feed over and over again. Let the lock
            # expire slowly until fetch_interval.
            #
            # self.refresh_lock.release()

            # Artificially slow down things to let the remote site
            # eventually recover while not bothering us too much.
            self.throttle_fetch_interval(0, 0, 1)
            self.update_last_fetch()
            self.save()
            return

        new_items, duplicates, mutualized = data

        if new_items == duplicates == mutualized == 0:

            with statsd.pipeline() as spipe:
                spipe.incr('feeds.refresh.fetch.global.unchanged')

        else:
            with statsd.pipeline() as spipe:
                spipe.incr('feeds.refresh.fetch.global.updated')

        if not force:
            # forcing the refresh is most often triggered by admins
            # and developers. It should not trigger the adaptative
            # throttling computations, because it generates a lot
            # of false-positive duplicates.
            self.throttle_fetch_interval(new_items, mutualized, duplicates)

        with statsd.pipeline() as spipe:
            spipe.incr('feeds.refresh.global.fetched', new_items)
            spipe.incr('feeds.refresh.global.duplicates', duplicates)
            spipe.incr('feeds.refresh.global.mutualized', mutualized)

        # Everything went fine, be sure to reset the "error counter".
        self.errors = []

        self.update_last_fetch()

        self.save()

        with statsd.pipeline() as spipe:
            spipe.incr('feeds.refresh.fetch.global.done')

        # As the last_fetch is now up-to-date, we can release the fetch lock.
        # If any other refresh job comes, it will check last_fetch and will
        # terminate if called too early.
        self.refresh_lock.release()

    def update_last_fetch(self):
        """ Allow to customize the last fetch datetime.

        This method exists to be overriden by “under development” classes,
        to allow not updating the last_fetch attribute, and continue
        fetching data forever on development machines.
        """

        self.date_last_fetch = now()

    def throttling_method(self, new_items, mutualized, duplicates):
        """ Calls throttle_fetch_interval() barely.

        This method can be safely overriden by subclasses to compute
        the new fetch interval with better precision. See
        the :class:`RssAtomFeed` class for a specific implementation.
        """

        return throttle_fetch_interval(self.fetch_interval,
                                       new_items,
                                       mutualized,
                                       duplicates)

    def throttle_fetch_interval(self, new_items, mutualized, duplicates):
        """ Compute a new fetch interval. """

        new_interval = self.throttling_method(new_items,
                                              mutualized,
                                              duplicates)

        if new_interval != self.fetch_interval:
            LOGGER.info(u'Fetch interval changed from %s to %s '
                        u'for feed %s (%s new article(s), %s '
                        u'duplicate(s)).', self.fetch_interval,
                        new_interval, self, new_items, duplicates)

            self.fetch_interval = new_interval


# ———————————————————————————————————————————————————————————————— Celery tasks


register_task_method(BaseFeed, BaseFeed.refresh,
                     globals(), queue=u'refresh')
register_task_method(BaseFeed, BaseFeed.update_all_items_count,
                     globals(), queue=u'low')
register_task_method(BaseFeed, BaseFeed.update_subscriptions_count,
                     globals(), queue=u'low')
register_task_method(BaseFeed, BaseFeed.update_recent_items_count,
                     globals(), queue=u'low')
register_task_method(BaseFeed, BaseFeed.update_latest_item_date_published,
                     globals(), queue=u'low')


# ————————————————————————————————————————————————————————————————————— Signals


def basefeed_pre_save(instance, **kwargs):
    """ Fix the JSON editing in the admin. """

    feed = instance

    if isinstance(feed.errors, unicode):
        # Workaround the admin keeping saving
        # unicode(unicode(…)) over and over.
        feed.errors = json.loads(feed.errors)

    if isinstance(feed.options, unicode):
        # Workaround the admin keeping saving
        # unicode(unicode(…)) over and over.
        feed.options = json.loads(feed.options)


def basefeed_post_save(instance, **kwargs):
    """ Do whatever useful on Feed.post_save(). """

    if not kwargs.get('created', False):
        return

    feed = instance

    try:
        feed.post_create_pre_refresh()

    except AttributeError:
        pass

    # if feed._db_name != settings.MONGODB_NAME_ARCHIVE:
        # Update the feed immediately after creation.

        # HEADS UP: this task name will be registered later
        # by the register_task_method() call.
    basefeed_refresh_task.delay(feed.id)  # NOQA

    try:
        feed.post_create_post_refresh()

    except AttributeError:
        pass

    statsd.gauge('feeds.counts.total', 1, delta=True)
    statsd.gauge('feeds.counts.open', 1, delta=True)


post_save.connect(basefeed_post_save, sender=BaseFeed)
pre_save.connect(basefeed_pre_save, sender=BaseFeed)


# ————————————————————————————————————————————————————————— Export class method


def basefeed_export_content_classmethod(cls, since, until=None, folder=None):
    """ Pull articles & feeds since :param:`param` and return them in a dict.

        if a feed has no new article, it's not represented at all. The returned
        dict is suitable to be converted to JSON.
    """

    from twitter import TwitterFeed

    def export_one_feed(feed, exported_items, subscription=None):

        if subscription is None:
            if hasattr(feed, 'url'):
                return OrderedDict(
                    id=unicode(feed.id),
                    name=feed.name,
                    url=feed.url,
                    thumbnail_url=feed.thumbnail.url
                    if feed.thumbnail else feed.thumbnail_url,
                    short_description=feed.short_description,
                    tags=[t.name for t in feed.tags.all()],
                    articles=exported_items,
                )
            else:
                return OrderedDict(
                    id=unicode(feed.id),
                    name=feed.name,
                    url=feed.uri,
                    thumbnail_url=feed.thumbnail.url
                    if feed.thumbnail else feed.thumbnail_url,
                    short_description=feed.short_description,
                    tags=[t.name for t in feed.tags.all()],
                    articles=exported_items,
                )

        if hasattr(feed, 'url'):
            return OrderedDict(
                id=unicode(feed.id),
                name=subscription.name,
                url=feed.url,
                thumbnail_url=subscription.thumbnail.url
                if subscription.thumbnail else subscription.thumbnail_url
                if subscription.thumbnail_url else feed.thumbnail.url
                if feed.thumbnail else feed.thumbnail_url,
                short_description=feed.short_description,
                tags=[t.name for t in subscription.tags.all()],
                articles=exported_items,
            )

        else:
            # Twitter feed ?
            return OrderedDict(
                id=unicode(feed.id),
                name=subscription.name,
                url=feed.uri,
                thumbnail_url=subscription.thumbnail.url
                if subscription.thumbnail else subscription.thumbnail_url,
                short_description=feed.short_description,
                tags=[t.name for t in subscription.tags.all()],
                articles=exported_items,
            )

    def export_one_item(item, related_to=None):

        if isinstance(item, Tweet):
            return OrderedDict(
                id=unicode(item.id),
                image_url=item.image_url if hasattr(item, '') else None,
                content=item.name,
                media=origin(item.origin),
                date_published=item.date_published
                or related_to.date_published,

                authors=[(a.name or a.origin_name)
                         for a in item.authors.all()],
                date_updated=None,
                language=item.language.dj_code
                if item.language else None,
                text_direction=item.text_direction,
                tags=[t.name for t in item.tags.all()],
            )
        else:
            return OrderedDict(
                id=unicode(item.id),
                title=item.name,
                pages_url=[item.url],
                image_url=item.image_url if hasattr(item, '') else None,
                excerpt=item.excerpt,
                content=item.content,
                media=origin(item.origin),
                content_type=content_type(item.content_type),
                date_published=item.date_published,

                authors=[(a.name or a.origin_name)
                         for a in item.authors.all()],
                date_updated=None,
                language=item.language.dj_code
                if item.language else None,
                text_direction=item.text_direction,
                tags=[t.name for t in item.tags.all()],
            )

    def origin(origin):

        if origin in (ORIGINS.FEEDPARSER, ORIGINS.GOOGLE_READER):
            return u'rss'

        if origin == ORIGINS.TWITTER:
            return u'twitter'

        if origin == ORIGINS.EMAIL_FEED:
            return u'email'

        # implicit:
        # if origin == (ORIGINS.NONE, ORIGINS.WEBIMPORT):
        return u'web'

    def content_type(content_type):

        if content_type == CONTENT_TYPES.MARKDOWN:
            return u'markdown'

        if content_type == CONTENT_TYPES.HTML:
            return u'html'

        if content_type == CONTENT_TYPES.IMAGE:
            return u'image'

        if content_type == CONTENT_TYPES.VIDEO:
            return u'video'

        if content_type == CONTENT_TYPES.BOOKMARK:
            return u'bookmark'

    if folder is None:
        active_feeds = BaseFeed.objects.filter(is_active=True,
                                               is_internal=False)
        active_feeds_count = active_feeds.count()

        folders = None

    else:
        folders = folder.get_descendants(include_self=True)

        active_feeds = BaseFeed.objects.filter(
            id__in=folder.user.all_subscriptions.filter(
                folders=folders).filter(
                    feed__is_active=True).values_list(
                        'feed_id', flat=True)
        ).select_related('items', 'tags')

    active_feeds_count = active_feeds.count()

    exported_websites = {}
    exported_feeds = []
    total_exported_items_count = 0

    if active_feeds_count:
        if folders:
            LOGGER.info(u'Starting feeds/items export procedure '
                        u'of %s folder(s) with %s active feeds…',
                        folders.count(), active_feeds_count)
        else:
            LOGGER.info(u'Starting feeds/items export procedure on %s '
                        u'active feeds…', active_feeds_count)
    else:
        LOGGER.warning(u'Not running export procedure, we have '
                       u'no active feed. Is this possible?')
        return

    for feed in active_feeds:

        related_fields = ['language', 'author', 'tags', ]

        if isinstance(feed, TwitterFeed):
            new_items = feed.good_items.tweet()
            related_fields.append('entities')

        else:
            new_items = feed.good_items

        # LOGGER.debug(u'Feed export: selected %s new items in feed %s.',
        #              new_items.count(), feed)

        if since:
            new_items = new_items.filter(
                date_published__gte=since)

        if until:
            new_items = new_items.filter(
                date_published__lt=until)

        new_items.select_related(*related_fields)

        new_items_count = new_items.count()

        if not new_items_count:
            continue

        exported_items = []

        for item in new_items:
            exported_items.append(export_one_item(item))

            if hasattr(item, 'entities'):
                for entity in item.entities.all():
                    exported_items.append(export_one_item(entity,
                                                          related_to=item))

        exported_items_count = len(exported_items)
        total_exported_items_count += exported_items_count

        try:
            website = feed.website

        except:
            # Not a website-aware feed.
            exported_website = None

        else:
            try:
                exported_website = exported_websites[website.url]

            except:
                exported_website = OrderedDict(
                    id=unicode(website.id),
                    name=website.name,
                    slug=website.slug,
                    url=website.url,
                    image_url=website.image_url,
                    short_description=website.short_description,
                )

                exported_websites[website.url] = exported_website

        if folder:
            subscription = feed.subscriptions.get(user=folder.user)

            exported_feed = export_one_feed(feed, exported_items, subscription)

        else:
            exported_feed = export_one_feed(feed, exported_items)

        if exported_website:
            exported_feed['website'] = exported_website

        exported_feeds.append(exported_feed)

        LOGGER.info(u'%s items exported in feed %s.',
                    exported_items_count, feed)

    exported_feeds_count = len(exported_feeds)

    LOGGER.info(u'%s feeds and %s total items exported.',
                exported_feeds_count, total_exported_items_count)

    return exported_feeds

setattr(BaseFeed, 'export_content',
        classmethod(basefeed_export_content_classmethod))
