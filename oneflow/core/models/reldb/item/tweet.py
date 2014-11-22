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
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

import json
import logging

from celery import task
from statsd import statsd
# from constance import config

from django.conf import settings
from django.db import models, IntegrityError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

from oneflow.base.utils import register_task_method
from oneflow.base.utils.http import clean_url
from oneflow.base.utils.dateutils import now, datetime

from ..common import ORIGINS

from base import (
    BaseItemQuerySet,
    BaseItemManager,
    BaseItem,
)

LOGGER = logging.getLogger(__name__)

MIGRATION_DATETIME = datetime(2014, 11, 1)


__all__ = [
    'Tweet',
    'create_tweet_from_url',
    'mark_tweet_deleted',

    # Tasks will be added below by register_task_method().
]


def create_tweet_from_url(url, feeds=None):
    """ PLEASE REVIEW. """

    raise NotImplementedError('Needs a full review / redesign for tweets.')

    if feeds is None:
        feeds = []

    elif not hasattr(feeds, '__iter__'):
        feeds = [feeds]

    # TODO: find tweet publication date while fetching content…
    # TODO: set Title during fetch…

    if settings.SITE_DOMAIN in url:
        # The following code should not fail, because the URL has
        # already been idiot-proof-checked in core.forms.selector
        #   .WebPagesImportForm.validate_url()
        read_id = url[-26:].split('/', 1)[1].replace('/', '')

        # Avoid an import cycle.
        from .read import Read

        # HEADS UP: we just patch the URL to benefit from all the
        # Tweet.create_tweet() mechanisms (eg. mutualization, etc).
        url = Read.objects.get(id=read_id).tweet.url

    try:
        new_tweet, created = Tweet.create_tweet(
            url=url.replace(' ', '%20'),
            title=_(u'Imported item from {0}').format(clean_url(url)),
            feeds=feeds, origin=ORIGINS.WEBIMPORT)

    except:
        # NOTE: duplication handling is already
        # taken care of in Tweet.create_tweet().
        LOGGER.exception(u'Tweet creation from URL %s failed.', url)
        return None, False

    mutualized = created is None

    if created or mutualized:
        for feed in feeds:
            feed.recent_items_count += 1
            feed.all_items_count += 1

    ze_now = now()

    for feed in feeds:
        feed.latest_item_date_published = ze_now

        # Even if the tweet wasn't created, we need to create reads.
        # In the case of a mutualized tweet, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.
        for subscription in feed.subscriptions.all():
            subscription.create_read(new_tweet, verbose=created)

    # Don't forget the parenthesis else we return ``False`` everytime.
    return new_tweet, created or (None if mutualized else False)


# —————————————————————————————————————————————————————————— Manager / QuerySet


def BaseItemQuerySet_tweet_method(self):
    """ Patch BaseItemQuerySet to know how to return tweets. """

    return self.instance_of(Tweet)


BaseItemQuerySet.tweet = BaseItemQuerySet_tweet_method


# ——————————————————————————————————————————————————————————————————————— Model

# BIG FAT WARNING: inheritance order matters. BaseItem must come first,
# else `create_post_task()` is not found by register_task_method().
class Tweet(BaseItem):

    """ A tweet.

    Cf. https://dev.twitter.com/overview/api/tweets
    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Tweet')
        verbose_name_plural = _(u'Tweets')

    objects = BaseItemManager()

    tweet_id = models.BigIntegerField(
        verbose_name=_(u'Tweet ID'),
        blank=True, unique=True, db_index=True
    )

    is_deleted = models.BooleanField(
        verbose_name=_(u'deleted from timeline'),
        # Should have a partial index.
        default=False, blank=True)

    # text → name
    # lang → BaseItem.language
    #
    # TODO:
    #   coordinates
    #   in_reply_to_screen_name
    #   in_reply_to_status_id
    #   in_reply_to_user_id
    #   place

    # —————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        return _(u'{0} ({1}, {2})').format(
            self.name[:40] + (self.name[40:] and u'…'), self.id, self.tweet_id)

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def is_good(self):
        """ Return True. A tweet is always good. """

        return True

    # ————————————————————————————————————————————————————————————————— Methods

    @classmethod
    def create_tweet(cls, TwitterAPI_item, feeds, **kwargs):
        """ Returns ``True`` if tweet created, ``False`` if a pure duplicate
            (already exists in the same feed), ``None`` if exists but not in
            the same feed. If more than one feed given, only returns ``True``
            or ``False`` (mutualized state is not checked). """

        title = TwitterAPI_item['text']
        tweet_id = TwitterAPI_item['id']
        cur_tweet = None
        new_tweet = None

        new_tweet = cls(name=title, tweet_id=tweet_id)

        try:
            new_tweet.save()

        except IntegrityError:
            cur_tweet = cls.objects.get(tweet_id=tweet_id)

        if cur_tweet:
            created_retval = False

            if len(feeds) == 1 and feeds[0] not in cur_tweet.feeds.all():
                # This tweet is already there, but has not yet been
                # fetched for this feed. It's mutualized, and as such
                # it is considered at partly new. At least, it's not
                # as bad as being a true duplicate.
                created_retval = None

                LOGGER.info(u'Mutualized tweet “%s” (ID: %s) in feed(s) %s.',
                            title, tweet_id,
                            u', '.join(unicode(f) for f in feeds))

            else:
                # No statsd, because we didn't create any record in database.
                LOGGER.info(u'Duplicate tweet “%s” (ID: %s) in feed(s) %s.',
                            title, tweet_id,
                            u', '.join(unicode(f) for f in feeds))

            try:
                cur_tweet.feeds.add(*feeds)

            except IntegrityError:
                # Race condition when backfill_if_needed() is run after
                # reception of first item in a stream, and they both create
                # the same tweet. One of them really
                pass

            return cur_tweet, created_retval

        if kwargs:
            for key, value in kwargs.items():
                setattr(new_tweet, key, value)

        if 'origin' not in kwargs:
            new_tweet.origin = ORIGINS.TWITTER

        new_tweet.save()

        LOGGER.info(u'Created tweet #%s in feed(s) %s.', new_tweet.tweet_id,
                    u', '.join(unicode(f) for f in feeds))

        # Tags & feeds are ManyToMany, they
        # need the tweet to be saved before.

        if feeds:
            try:
                new_tweet.feeds.add(*feeds)

            except IntegrityError:
                # Race condition: see some lines above.
                pass

        new_tweet.add_original_data('twitter',
                                    json.dumps(TwitterAPI_item),
                                    launch_task=True)

        return new_tweet, True

    def fetch_entities(self):
        """ Fetch Tweet entities. """

        LOGGER.warning(u'Please implement Tweet media fetching (%s).', self)

    def post_create_task(self, apply_now=False):
        """ Method meant to be run from a celery task. """

        fetch_task = globals()['tweet_fetch_entities_task']

        if apply_now:
            fetch_task.apply((self.id, ))

        else:
            fetch_task.delay(self.id)

# ———————————————————————————————————————————————————————————————— Celery Tasks


register_task_method(Tweet, Tweet.post_create_task,
                     globals(), queue=u'create')
register_task_method(Tweet, Tweet.fetch_entities,
                     globals(), queue=u'fetch')

# register_task_method(Tweet, Tweet.find_image,
#                      globals(), queue=u'fetch', default_retry_delay=3600)


@task(queue='background')
def mark_tweet_deleted(tweet_id):

        try:
            tweet = Tweet.objects.get(tweet_id=tweet_id)

        except:
            LOGGER.warning(u'Unknown tweet to delete: %s', tweet_id)

        else:
            tweet.is_deleted = True
            tweet.save()

            statsd.gauge('tweets.counts.deleted', 1, delta=True)
            LOGGER.info(u'Tweet %s marked as deleted.', tweet)

# ————————————————————————————————————————————————————————————————————— Signals


def tweet_pre_save(instance, **kwargs):
    """ Make a slug if none. """

    tweet = instance

    if not tweet.slug:
        tweet.slug = slugify(tweet.name)


def tweet_post_save(instance, **kwargs):

    tweet = instance

    if kwargs.get('created', False):

        with statsd.pipeline() as spipe:
            spipe.gauge('tweets.counts.total', 1, delta=True)

        globals()['tweet_post_create_task'].delay(tweet.id)  # NOQA


def tweet_pre_delete(instance, **kwargs):

    with statsd.pipeline() as spipe:
        spipe.gauge('tweets.counts.total', -1, delta=True)


pre_delete.connect(tweet_pre_delete, sender=Tweet)
pre_save.connect(tweet_pre_save, sender=Tweet)
post_save.connect(tweet_post_save, sender=Tweet)
