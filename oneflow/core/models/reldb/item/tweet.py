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
from django.db import models, transaction, IntegrityError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

from oneflow.base.utils import register_task_method
from oneflow.base.utils.http import clean_url
from oneflow.base.utils.dateutils import now, datetime

from ..common import ORIGINS, CONTENT_TYPES
from ..author import Author

from base import (
    BaseItemQuerySet,
    BaseItemManager,
    BaseItem,
    baseitem_create_reads_task,
)


LOGGER = logging.getLogger(__name__)

MIGRATION_DATETIME = datetime(2014, 11, 1)


__all__ = [
    'Tweet',
    'create_tweet_from_id',
    'mark_tweet_deleted',

    # Tasks will be added below by register_task_method().
]


def create_tweet_from_id(tweet_id, feeds=None, origin=None):
    """ From a Tweet ID, create a 1flow tweet via the REST API.


    https://dev.twitter.com/rest/reference/get/statuses/show/%3Aid

    .. todo:: use http://celery.readthedocs.org/en/latest/reference/celery.contrib.batches.html  # NOQA
        to bulk get statuses and not exhaust the API Quota.
    """

    raise NotImplementedError('Needs a full review / redesign for tweets.')

    if feeds is None:
        feeds = []

    elif not hasattr(feeds, '__iter__'):
        feeds = [feeds]

    # TODO: find tweet publication date while fetching content…
    # TODO: set Title during fetch…

    try:
        new_tweet, created = Tweet.create_tweet(
            url=tweet_id.replace(' ', '%20'),
            title=_(u'Imported item from {0}').format(clean_url(tweet_id)),
            feeds=feeds, origin=ORIGINS.WEBIMPORT)

    except:
        # NOTE: duplication handling is already
        # taken care of in Tweet.create_tweet().
        LOGGER.exception(u'Tweet creation from URL %s failed.', tweet_id)
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
        default=False, blank=True
    )

    entities_fetched = models.BooleanField(
        verbose_name=_(u'Entities fetched?'),

        # Should have a partial index.
        default=False, blank=True
    )

    entities = models.ManyToManyField(
        BaseItem, blank=True, null=True,
        verbose_name=_(u'Entities'),
        related_name='tweets'
    )

    mentions = models.ManyToManyField(
        Author, blank=True, null=True,
        verbose_name=_(u'mentions'),
        related_name='mentions'
    )

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

    # —————————————————————————————————————————— Article backward compatibility
    #       Only for rendering, should vanish when we have dedicated templates.

    @property
    def url(self):
        """ Be compatible with articles for rendering. """
        try:
            username = self.authors.get().username
        except:
            username = u'UNKNOWN'

        return u'http://twitter.com/{1}/status/{2}'.format(
            username,
            self.tweet_id)

    @property
    def content_type(self):
        """ Be compatible with articles for rendering. """

        return CONTENT_TYPES.MARKDOWN

    @property
    def content(self):
        """ Be compatible with articles for rendering. """

        content = self.name[:]

        json_tweet = self.original_data.twitter_hydrated
        entities = json_tweet.get('entities', {})

        for entity_url in entities.get('urls', []):

            indices = entity_url['indices']
            LOGGER.debug('replace %s', indices)

            content = content[:indices[0]] + u'[{0}]({1})'.format(
                entity_url['display_url'], entity_url['expanded_url']
            ) + content[indices[1]:]

            #
            # TODO: indexes love when there are more than one…
            #
            break

        return content

    # ————————————————————————————————————————————————————————————————— Methods

    @classmethod
    def create_tweet(cls, TwitterAPI_item, feeds, **kwargs):
        """ Returns ``True`` if tweet created, ``False`` if a pure duplicate
            (already exists in the same feed), ``None`` if exists but not in
            the same feed. If more than one feed given, only returns ``True``
            or ``False`` (mutualized state is not checked). """

        title = TwitterAPI_item['text']
        tweet_id = TwitterAPI_item['id']

        defaults = {
            'name': title,
            'origin': kwargs.pop('origin', ORIGINS.TWITTER)
        }

        defaults.update(kwargs)

        tweet, created = cls.objects.get_or_create(tweet_id=tweet_id,
                                                   defaults=defaults)

        if created:
            LOGGER.info(u'Created tweet #%s in feed(s) %s.', tweet_id,
                        u', '.join(unicode(f) for f in feeds))

            if feeds:
                try:
                    with transaction.atomic():
                        tweet.feeds.add(*feeds)

                except IntegrityError:
                    LOGGER.exception(u'Integrity error on created tweet #%s',
                                     tweet_id)
                    pass

            tweet.add_original_data('twitter',
                                    json.dumps(TwitterAPI_item),
                                    launch_task=True)

            return tweet, True

        # —————————————————————————————————————————————————————— existing tweet

        # Get a change to catch a duplicate if workers were fast.
        if tweet.duplicate_of_id:
            LOGGER.info(u'Swaping duplicate tweet #%s with master #%s on '
                        u'the fly.', tweet.id, tweet.duplicate_of_id)

            tweet = tweet.duplicate_of

        created_retval = False

        previous_feeds_count = tweet.feeds.count()

        try:
            with transaction.atomic():
                tweet.feeds.add(*feeds)

        except IntegrityError:
            # Race condition when backfill_if_needed() is run after
            # reception of first item in a stream, and they both create
            # the same tweet.
            LOGGER.exception(u'Integrity error when adding feeds %s to '
                             u'tweet #%s', feeds, tweet_id)

        else:
            if tweet.feeds.count() > previous_feeds_count:
                # This tweet is already there, but has not yet been
                # fetched for this feed. It's mutualized, and as such
                # it is considered at partly new. At least, it's not
                # as bad as being a true duplicate.
                created_retval = None

                LOGGER.info(u'Mutualized tweet #%s #%s in feed(s) %s.',
                            tweet_id, tweet.id,
                            u', '.join(unicode(f) for f in feeds))

                tweet.create_reads(feeds=feeds)

            else:
                # No statsd, because we didn't create any record in database.
                LOGGER.info(u'Duplicate tweet “%s” #%s #%s in feed(s) %s.',
                            title, tweet_id, tweet.id,
                            u', '.join(unicode(f) for f in feeds))

        return tweet, created_retval

    def fetch_entities(self, entities=None, commit=True):
        """ Fetch Tweet entities. """

        # u'entities': {
        #     u'hashtags': [],
        #     u'symbols': [],
        #     u'urls': [
        #       {
        #           u'display_url': u'oncletom.io',
        #           u'expanded_url': u'http://oncletom.io',
        #           u'indices': [0, 22],
        #           u'url': u'http://t.co/xdbcCzdQOn'
        #       }
        #     ],
        #     u'user_mentions': []
        # },

        if self.entities_fetched:
            LOGGER.info(u'%s: entities already fetched.', self)
            # return

        if entities is None:
            entities = self.original_data.twitter_hydrated['entities']

        all_went_ok = True

        for entities_name, fetch_entities_method in (
            ('urls', self.fetch_entities_urls, ),
            ('media', self.fetch_entities_media, ),
            ('user_mentions', self.connect_mentions, ),
        ):
            entities_values = entities.get(entities_name, None)

            if entities_values:
                if not fetch_entities_method(entities_values):
                    all_went_ok = False

        if all_went_ok:
            self.entities_fetched = True

            if commit:
                self.save()

    def fetch_entities_urls(self, entities_urls):
        """ Fetch URLs entities, and add the created items to self.entities. """

        from create import create_item_from_url

        all_went_ok = True

        update_original_data = False
        new_entities_urls = []

        for entity_url in entities_urls:
            try:
                url = entity_url['expanded_url']

                item, created = create_item_from_url(
                    url=url,
                    feeds=self.feeds.all(),
                    origin=ORIGINS.TWITTER
                )

                if item.url != url:
                    # Our absolutizer has resolved the URL more than it was.
                    entity_url['expanded_url'] = item.url
                    entity_url['display_url'] = u'{0}/a/{1}'.format(
                        settings.SITE_DOMAIN, item.id)
                    update_original_data = True

                new_entities_urls.append(entity_url)

                try:
                    with transaction.atomic():
                        self.entities.add(item)

                except:
                    LOGGER.error(u'Could not add entity %s to tweet #%s',
                                 item.id, self.id)

            except:
                all_went_ok = False
                LOGGER.exception(u'Could not fetch URL entity %s of '
                                 u'tweet #%s', url, self.id)

        if update_original_data:
            tweet_original_data = self.original_data.twitter_hydrated
            entities_orig = tweet_original_data['entities']
            entities_orig['urls.orig.1flow'] = entities_orig['urls'][:]
            entities_orig['urls'] = new_entities_urls
            tweet_original_data['entities'] = entities_orig
            self.original_data.twitter = json.dumps(tweet_original_data)

            self.original_data.save()

            LOGGER.info(u'%s #%s: updated original data because URLs changed.',
                        self._meta.model.__name__, self.id)

        return all_went_ok

    def fetch_entities_media(self, media):
        """ Fetch media entities. """
        # {u'hashtags': [],
        #  u'media': [
        #       {
        #           u'display_url': u'pic.twitter.com/eOIPsqpcfr',
        #           u'expanded_url': u'http://twitter.com/ScPoLille/status/535408882081083392/photo/1',
        #           u'id': 535408873046568961,
        #           u'id_str': u'535408873046568961',
        #           u'indices': [139, 140],
        #           u'media_url': u'http://pbs.twimg.com/media/B24niIeIcAEle7X.jpg',
        #           u'media_url_https': u'https://pbs.twimg.com/media/B24niIeIcAEle7X.jpg',
        #           u'sizes': {u'large': {u'h': 768, u'resize': u'fit', u'w': 1024},
        #            u'medium': {u'h': 450, u'resize': u'fit', u'w': 600},
        #            u'small': {u'h': 255, u'resize': u'fit', u'w': 340},
        #            u'thumb': {u'h': 150, u'resize': u'crop', u'w': 150}},
        #           u'source_status_id': 535408882081083392,
        #           u'source_status_id_str': u'535408882081083392',
        #           u'type': u'photo',
        #           u'url': u'http://t.co/eOIPsqpcfr'
        #      }
        #  ],
        #  u'symbols': [],
        #  u'urls': [],
        # }

        pass

    def connect_mentions(self, user_mentions):
        """ Connect mentions to the current tweet. """

        #  u'user_mentions': [{u'id': 518750123,
        #    u'id_str': u'518750123',
        #    u'indices': [3, 13],
        #    u'name': u'Sciences Po Lille',
        #    u'screen_name': u'ScPoLille'},
        #   {u'id': 311880926,
        #    u'id_str': u'311880926',
        #    u'indices': [119, 126],
        #    u'name': u'Etalab',
        #    u'screen_name': u'Etalab'}]

        all_went_ok = True

        for user_mention in user_mentions:
            try:
                author = Author.get_author_from_twitter_user(user_mention)

                self.mentions.add(author)

            except:
                all_went_ok = False
                LOGGER.exception(u'Could not connect user mention '
                                 u'%s in tweet %s', user_mention, self)

        return all_went_ok

    def post_create_task(self, apply_now=False):
        """ Method meant to be run from a celery task. """

        fetch_task = globals()['tweet_fetch_entities_task']

        if apply_now:
            baseitem_create_reads_task.apply((self.id, ))
            fetch_task.apply((self.id, ))

        else:

            fetch_task.delay(self.id)
            baseitem_create_reads_task.si(self.id),


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
