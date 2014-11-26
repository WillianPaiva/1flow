# -*- coding: utf-8 -*-
u"""
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

import logging

from statsd import statsd
from constance import config

from django.conf import settings  # NOQA
from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from oneflow.base.utils import register_task_method
from oneflow.base.utils.dateutils import (
    naturaldelta, now, timedelta,
    twitter_datestring_to_datetime_utc as twitter_datetime
)

from ..common import REDIS
from ..account import TwitterAccount
from ..item import Tweet, mark_tweet_deleted

from base import (
    BaseFeedQuerySet,
    BaseFeedManager,
    BaseFeed,
    basefeed_pre_save,
)

from common import (
    TWITTER_MATCH_ACTIONS,
    TWITTER_FINISH_ACTIONS,
    TWITTER_RULES_OPERATIONS,

    TWITTER_MATCH_ACTION_DEFAULT,
    TWITTER_FINISH_ACTION_DEFAULT,
    TWITTER_RULES_OPERATION_DEFAULT,
)

LOGGER = logging.getLogger(__name__)


__all__ = [
    'TwitterFeed',

    # tasks will be added by register_task_method(),
]

# —————————————————————————————————————————————————————————— Manager / QuerySet


def BaseFeedQuerySet_twitter_method(self):
    """ Patch BaseFeedQuerySet to know how to return Twitter accounts. """

    return self.instance_of(TwitterFeed)


def BaseFeedQuerySet_user_made_method(self):
    """ Return Twitter feeds created by the user.

    Eg. not the ones created by the system.
    """

    return self.exclude(is_timeline=True).filter(uri=None)

BaseFeedQuerySet.twitter = BaseFeedQuerySet_twitter_method
BaseFeedQuerySet.user_made = BaseFeedQuerySet_user_made_method


# ——————————————————————————————————————————————————————————————————————— Model


class TwitterFeed(BaseFeed):

    """ Configuration of a twitter-based 1flow feed. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Twitter feed')
        verbose_name_plural = _(u'Twitter feeds')

    # We override the refresh lock interval. As Twitter feed refresh is
    # permanent, we will *always* release the lock when stopping refresh,
    # to allow a new refresh to start right away after. In the meantime,
    # we must avoid launching 2 parallel refresh tasks, and there is a risk
    # the lock is released while consume() task blocks on user stream of
    # very-low-trafic timeline. Thus, we must simulate a non-expiring lock.
    REFRESH_LOCK_INTERVAL = 3600 * 24 * 31

    objects = BaseFeedManager()

    #
    # HEADS UP: `.user` is inherited from BaseFeed.
    #

    account = models.ManyToManyField(
        TwitterAccount, null=True, blank=True,
        verbose_name=_(u'Twitter accounts'), related_name='twitter_feeds',
        help_text=_(u"To apply this rule to all accounts, "
                    u"just don't choose any."))

    # types:
    # https://dev.twitter.com/streaming/reference/get/user
    # https://dev.twitter.com/streaming/reference/post/statuses/filter

    uri = models.CharField(
        verbose_name=_(u'Twitter URI'),
        max_length=255, null=True, blank=True, unique=True,
        help_text=_(u'Twitter URI of the feed. Used for lists and '
                    u'other “bare” twitter items, else unuse.d'))

    is_timeline = models.BooleanField(
        verbose_name=_(u'Timeline'),
        default=False, blank=True,
        help_text=_(u'True if the feed is the user timeline. There is only '
                    u'one feed of this type per Twitter account.')
    )

    is_backfilled = models.BooleanField(
        verbose_name=_(u'Backfill this feed'),
        default=False, blank=True,
        help_text=_(u'Enable if you want to try to get as much information '
                    u'as possible from the past. (Default: {0}).').format(
                        config.TWITTER_FEEDS_BACKFILL_ENABLED_DEFAULT)
    )

    backfill_completed = models.IntegerField(
        verbose_name=_(u'completed backfill range'),
        null=True, blank=True,
        help_text=_(u'This field will be filled by the system while it '
                    u'rewinds tweets until the start of the stream. At '
                    u'the end of the process, it will equal '
                    u'config.TWITTER_BACKFILL_ALLOWED_REWIND_RANGE to '
                    u'signify the history backfilling is complete.')
    )

    track_terms = models.TextField(
        verbose_name=_(u'Track terms'),
        null=True, blank=True,
        help_text=_(u'phrases separated by spaces and commas, each of them '
                    u'beiing no more than 60 characters long. See '
                    u'http://bit.ly/twitter-track for more information.')
    )

    track_locations = models.TextField(
        verbose_name=_(u'Track locations'),
        null=True, blank=True,
        help_text=_(u'A comma-separated list of longitude,latitude pairs '
                    u'specifying a set of bounding boxes. See '
                    u'http://bit.ly/twitter-locations for more information.')
    )

    match_action = models.IntegerField(
        verbose_name=_(u'Match action'),
        default=TWITTER_MATCH_ACTION_DEFAULT,
        choices=TWITTER_MATCH_ACTIONS.get_choices(),
        help_text=_(u'Defines a global match action '
                    u'for all rules of the feed. You '
                    u'can override this value at the '
                    u'rule level, only for the ones '
                    u'you want.'))

    finish_action = models.IntegerField(
        verbose_name=_(u'Finish action'),
        default=TWITTER_FINISH_ACTION_DEFAULT,
        choices=TWITTER_FINISH_ACTIONS.get_choices(),
        help_text=_(u'Defines a global finish action '
                    u'for all rules of the feed. You '
                    u'can override this value at the '
                    u'rule level, only for the ones '
                    u'you want.'))

    rules_operation = models.IntegerField(
        verbose_name=_(u'Rules operation'),
        default=TWITTER_RULES_OPERATION_DEFAULT,
        choices=TWITTER_RULES_OPERATIONS.get_choices(),
        help_text=_(u'Condition between rules or rules groups.'))

    #
    # HEADS UP: 20141004, these fields are not used yet in the engine.
    #
    scrape_whitelist = models.CharField(
        null=True, blank=True, max_length=1024,
        verbose_name=_(u'Scrape whitelist'),
        help_text=_(u'Eventually refine URLs you want to scrape in '
                    u'the email body. Type a list of valid URLs '
                    u'patterns, and start with “re:” if you want '
                    u'to use a regular expression.'))

    scrape_blacklist = models.BooleanField(
        default=True, blank=True,
        verbose_name=_(u'Use scrape blacklist'),
        help_text=_(u'Use 1flow adblocker to avoid scrapeing '
                    u'email adds, unsubscribe links and the like.'))

    # ——————————————————————————————————————————————————————————— Class methods

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def is_list(self):
        """ Return True if the current feed is a twitter list. """

        return bool(self.uri)

    @property
    def redis_good_periods_key(self):
        """ Return a string for redis keying on our Twitter good periods."""

        return u'tf:{0}:gdper'.format(self.id)

    @property
    def redis_time_ids_key(self):
        """ Return a string for redis keying on our Twitter SINCE/MAX values."""

        return u'tf:{0}:timeids'.format(self.id)

    @property
    def latest_id(self):
        """ Return our since ID. """

        return self.get_time_tweet_id(latest=True)

    @property
    def oldest_id(self):
        """ Return our max ID. """

        return self.get_time_tweet_id(latest=False)

    @property
    def good_periods_count(self):
        """ Return our good periods count. """

        return int(REDIS.scard(self.redis_good_periods_key) or 0)

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'TwitterFeed “{0}” of user {1} (#{2})'.format(
            self.name, self.user, self.id)

    # ————————————————————————————————————————————————————————— Redis internals

    def get_time_tweet_id(self, latest=None):
        """ Generic get time ID for since & max.

        For easier access, use :meth:`latest_id` and :meth:`oldest_id`
        properties.

        ..note:: If latest is ``None`` (which is the default), return a
            dict of both latest & max.
        """

        if latest:
            result = REDIS.hget(self.redis_time_ids_key, 'latest')

            if result is None:
                return None

            return int(result)

        elif latest is False:
            result = REDIS.hget(self.redis_time_ids_key, 'oldest')

            if result is None:
                return None

            return int(result)

        return REDIS.hgetall(self.redis_time_ids_key)

    def set_time_tweet_id(self, which_id, latest=True):
        """ Generic set time ID for latest & oldest. """

        if latest:
            return REDIS.hset(self.redis_time_ids_key, 'latest', which_id)

        return REDIS.hset(self.redis_time_ids_key, 'oldest', which_id)

    def set_latest_id(self, which_id):
        """ Set our twitter latest ID. """

        return self.set_time_tweet_id(which_id, latest=True)

    def set_oldest_id(self, which_id):
        """ Set our twitter oldest ID. """

        return self.set_time_tweet_id(which_id, latest=False)

    def record_good_period(self, start, end):
        """ Record a good period into redis. """

        REDIS.sadd(self.redis_good_periods_key, (start, end, ))

    def check_new_good_period(self, period_start_item, period_end_item):
        """ Check if the period (start, end) is OK to record.

        “good periods” offer coverage of consecutive tweets, allowing
        one day to eventually check timeline to guarantee their consistency
        and non-missing tweets in covered periods.

        .. todo:: one day, finish the coverage feature, by analyzing good
            periods, merge them, and backfill non-covered periods. This
            will work on timelines, partially on lists (because list
            members vary over time), and will be practically undoable on
            search streams because of quota constraints. And anyway, except
            for history concerns, doing it on search streams seems pretty
            pointless to me.
        """

        if period_start_item and period_end_item and (
                period_start_item != period_end_item):

            # FUTURE: do something with these.
            self.record_good_period(period_start_item, period_end_item)

            if settings.DEBUG:
                LOGGER.info(u'%s: good period %s-%s recorded, %s total.',
                            self, period_start_item, period_end_item,
                            self.good_periods_count)

    # ———————————————————————————————————————————————————— BaseFeed connections

    def refresh_must_abort_internal(self):
        """ Specific conditions where an Twitter feed should not refresh. """

        if config.FEED_FETCH_TWITTER_DISABLED:
            LOGGER.info(u'Twitter feed %s refresh disabled by dynamic '
                        u'configuration.', self)
            return True

        return False

    def refresh_feed_internal(self, force=False):
        """ Refresh a twitter feed. """

        LOGGER.info(u'Refreshing Twitter feed %s…', self)

        if self.is_timeline or self.uri \
                or self.track_terms or self.track_locations:

            if self.is_backfilled:
                globals()['twitterfeed_backfill_task'].delay(self.id)
                # LOGGER.debug(u'%s: launched backfill() task.', self)

            globals()['twitterfeed_consume_task'].delay(self.id)
            # LOGGER.debug(u'%s: launched consume() task.', self)

            # Tell BaseFeed.refresh() we are completely autonomous.
            return True

    # —————————————————————————————————————— high-level Twitter stream handling

    def __handle_one_item(self, item, backfilling=False):
        """ Handle one item from a twitter stream. """

        processed = False
        exit_loop = False

        if 'text' in item:
            processed = True

            # If the tweet flow is too high,
            # this should go into a celery task.
            tweet, created = Tweet.create_tweet(item, [self])

            if created:
                for subscription in self.subscriptions.all():
                    subscription.create_read(tweet,
                                             verbose=created)
            else:
                # a duplicate tweet. This should not
                # happen, and twitter doesn't like this.
                exit_loop = not backfilling

            # Duplicate or created, we will update
            # the counters, to not hit it again.
            tweet_id = item['id']

            if backfilling:

                oldest_id = self.oldest_id

                if oldest_id is None or tweet_id < oldest_id:
                    # Forward to latest tweet
                    self.set_oldest_id(tweet_id)
            else:

                latest_id = self.latest_id

                if latest_id is None or tweet_id > self.latest_id:
                    # Forward to latest tweet
                    self.set_latest_id(tweet_id)

        elif 'code' in item:
            if item['code'] == 88:
                # {u'message': u'Rate limit exceeded', u'code': 88}
                LOGGER.error(u'%s: disconnecting while %s because %s', self,
                             u'backfilling' if backfilling else u'consuming',
                             item['message'])
                exit_loop = True

        elif 'warning' in item:
            percent = item['percent_full']

            if percent > 75:
                LOGGER.error(u'%s: Remote queue %s%% '
                             u'full, disconnecting.',
                             self, percent)
                exit_loop = True

            else:
                LOGGER.warning(u'%s: stall warning sent (%s%% '
                               u'full)', self, percent)

        elif 'delete' in item:
            try:
                mark_tweet_deleted.delay(
                    item['delete']['status']['id'])

            except:
                LOGGER.exception(u'Unable to delete tweet '
                                 u'from item %s', item)

        elif 'limit' in item:

            # TODO: create a LogItem(BaseItem) and log this with self.latest_id
            #       to be eventually able to get the items back with the search
            #       REST API afterwards.

            LOGGER.warning(u'%s: %s tweets missed',
                           item['limit'].get('track'))

        elif 'disconnect' in item:
            LOGGER.error(u'%s: disconnecting because %s',
                         self, item['disconnect'].get('reason'))
            exit_loop = True

        else:
            LOGGER.exception(u'%s: unhandled item: %s', self, item)

        # LOGGER.debug(u'%s: returning %s, %s', self, processed, exit_loop)

        return processed, exit_loop

    def __consume_items(self, api_path, parameters=None, backfilling=False):
        """ Consume tweets from a stream (public/user).

        This is an internal method, called from :meth:`consume`.
        """

        def format_quota(quota):
            if quota['remaining'] is None:
                return u' (no quota information)'

            if quota['remaining']:
                return u'; quota: %s call(s) remaining' % quota['remaining']

            else:
                return u'; quota exhausted, reset in %s' % (
                    naturaldelta(now() - quota['reset'])
                )

        def backfill_if_needed(old_latest, max_id):
            """ See if we need to backfill, or not. """

            # If we already have a latest_id, it means we connected
            # before. Thus, we check if a backfill is needed between
            # previous session and now. If latest recorded and current
            # are different, we could eventually have missed something.
            # → BACKFILL.
            #
            # If we don't have a latest_id, it's our first
            # connection ever. Backfilling is for history, and
            # has already been launched by consume(), to not
            # wait for an hypothetical first item in low-trafic
            # streams. → NO ACTION

            if old_latest and old_latest < max_id:
                globals()[
                    'twitterfeed_backfill_task'
                ].apply_async(
                    args=(self.id, ),
                    kwargs={
                        'since_id': old_latest,
                        'max_id': max_id - 1,
                    }
                )

        LOGGER.info(u'%s: starting consume() %sloop on %s(%s)',
                    self,
                    u'for backfilling ' if backfilling else u'',
                    api_path,
                    u'' if parameters is None
                    else ', '.join(u'{0}: {1}'.format(k, v)
                                   for k, v in parameters.items()))

        # We create it here to have it in scope to get quota at the end.
        result = None

        if parameters is None:
            parameters = {}

        exit_loop = False

        max_rewind_range = config.TWITTER_BACKFILL_ALLOWED_REWIND_RANGE
        max_rewind_range_as_dt_from_now = (
            now() - timedelta(days=max_rewind_range * 7))

        infinite_count = 0
        all_processed = 0
        cur_processed = 0

        old_latest = self.latest_id
        last_item = None

        if self.account.exists():
            twitter_account = self.account.order_by('?').first()

        else:
            twitter_account = self.user.accounts.twitter().order_by('?').first()

        LOGGER.debug(u'%s: consuming via account %s.', self, twitter_account)

        if not backfilling:
            self.update_last_fetch()
            self.save()

        with twitter_account as tweetapi:
            while True:
                LOGGER.debug(u'%s: %s (loop #%s)…', self,
                             u'backfilling' if backfilling else u'consuming',
                             infinite_count)
                infinite_count += 1

                try:
                    if parameters:
                        result = tweetapi.request(api_path, parameters)
                    else:
                        result = tweetapi.request(api_path)

                    if result.get_rest_quota()['remaining'] == 0:
                        LOGGER.error(u'%s: quota exhausted, exiting to '
                                     u'postpone processing.', self)
                        break

                    for item in result.get_iterator():

                        processed, exit_loop = self.__handle_one_item(
                            item, backfilling=backfilling)

                        if processed:
                            if cur_processed == 0 and not backfilling:
                                # At the first received item while streaming,
                                # we need to check if backfill is needed.
                                backfill_if_needed(old_latest, item['id'])

                            cur_processed += 1

                        if backfilling:
                            # Backfilling doesn't touch the lock.
                            continue

                        if config.FEED_FETCH_TWITTER_DISABLED:
                            LOGGER.warning(
                                u'%s: exiting because '
                                u'config.FEED_FETCH_TWITTER_DISABLED is '
                                u'now true.', self)
                            exit_loop = True

                        last_item = item

                        if exit_loop:
                            break

                    if backfilling and max_rewind_range:
                        if last_item \
                            and twitter_datetime(last_item['created_at']) \
                                < max_rewind_range_as_dt_from_now:
                            self.backfill_completed = max_rewind_range
                            self.save()

                            LOGGER.info(u'%s: backfilled to the maximum '
                                        u'allowed.', self)
                            break

                    if cur_processed == 0:

                        if backfilling:
                            # NOTE: determining the reach of start of stream
                            # on lists is not reliable at all. For now we just
                            # abort to avoid mode damage (API exhaustion, etc).

                            if parameters.get('since_id', None):
                                LOGGER.info(u'%s: reached end of available '
                                            u'data on the Twitter side.',
                                            self)
                                self.backfill_completed = 0
                                self.save()

                        else:
                            # We got out of the loop without getting any new
                            # item. Just bail out, else we will keep polling
                            # Twitter again and again, exhausting our REST
                            # API quota, hitting duplicates in our database.
                            LOGGER.info(u'%s: no new item in stream.', self)

                        break

                    else:
                        # We got out of the loop, with max items (200)
                        # reached, or at least more than 0. Try to
                        # {fore,back}fill again to fill the gap. If we
                        # were already at max items, we'll got 0 and
                        # then stop. Else, the process will continue.
                        # Only if we were already at end will it cost
                        # us an API call for nothing.
                        if backfilling:
                            parameters['max_id'] = self.oldest_id - 1

                        else:
                            parameters['since_id'] = self.latest_id

                    if not backfilling:
                        self.update_last_fetch()
                        self.save()

                        # TODO: this creates a race condition. we should
                        # just re-aquire the lock with celery current task
                        # ID, but it's not available in the current scope
                        # (we are a method in the task, not the task
                        # itself)…
                        self.refresh_lock.release()

                        if not self.refresh_lock.acquire():
                            LOGGER.critical(u'%s: could not re-acquire '
                                            u'our own lock, abruptly '
                                            u'terminating stream '
                                            u'consumption.', self)
                            exit_loop = True

                except KeyboardInterrupt:
                    LOGGER.warning(u'Interrupting stream consumption '
                                   u'at user request.')
                    break

                except Exception:
                    #
                    # TODO: handle network errors, set last_fetch,
                    #       last TID, and exit for a while if relevant.
                    #       Else, just continue and let the stream flow.
                    #
                    LOGGER.exception(u'%s: exception in loop #%s after '
                                     u'having consumed %s item(s), '
                                     u're-starting…', self,
                                     infinite_count, cur_processed)

                all_processed += cur_processed
                cur_processed = 0

                if exit_loop:
                    break

        LOGGER.info(u'%s: exiting %sconsume() after %s items processed '
                    u'in %s loop(s)%s.', self,
                    u'backfilling ' if backfilling else u'',
                    all_processed, infinite_count,
                    format_quota(result.get_rest_quota()))

    def consume(self):
        u""" Consume a Twitter stream, forward, and permanently.

        This method, run as a celery task, can be stopped by many means:

        - set config.FEED_FETCH_TWITTER_DISABLED to ``True``. The method
          will exit as soon as possible, and will not be relaunched by
          the feed refresher.
        - temporarily, by stopping the celery “permanent” worker.

        - if a network error occur.
        - or if Twitter asks us to.

        The method it self can eventually crash or exit cleanly in some
        rare conditions (for example if API calls quota is exhausted).
        It will be relaunched by the global fetcher.

        .. note:: this method is available as a celery task
            via :func:`twitterfeed_consume_task`.
        """

        period_start_item = self.latest_id

        try:
            if self.is_timeline:
                # if settings.DEBUG:
                #     self.__consume_items('statuses/sample',
                #                          {'stall_warning': 'true'})
                # else:
                self.__consume_items('user')

            elif self.uri:
                # We have a twitter list.
                owner_screen_name, _, slug = self.uri[1:].split(u'/')

                parameters = {
                    'include_rts': 1,
                    'slug': slug,
                    'owner_screen_name': owner_screen_name,
                }

                # HEADS UP: lists/statuses is a REST API call. We need a
                #           since_id, else we keep getting always the same
                #           results at the top.

                latest_id = self.latest_id

                if latest_id:
                    parameters['since_id'] = latest_id + 1

                self.__consume_items('lists/statuses', parameters)

            elif self.track_terms or self.track_locations:

                parameters = {}

                if self.track_terms:
                    parameters['track'] = self.track_terms

                if self.track_locations:
                    parameters['locations'] = self.track_locations

                # Ex: Canéjan
                #               44.7800
                # -0.6890,                      -0.6269
                #               44.7343
                #
                # Eg. -0.6890,44.7343,-0.6269,44.7800
                # Terms: Canéjan,Canejan
                # TODO: implement 'following' to make more than
                #       10k users a reality.

                # https://dev.twitter.com/streaming/overview/request-parameters#locations  # NOQA
                self.__consume_items('statuses/filter', parameters)

        finally:
            self.check_new_good_period(period_start_item, self.latest_id)

            # HEADS UP: we explicitely release the lock
            # to allow a new refresh to start ASAP. If
            # we stopped, something went wrong and we have
            # to catch up the twitter feed as fast as p—
            self.refresh_lock.release()

            if settings.DEBUG:
                LOGGER.info(u'%s: released refresh lock.', self)

    def backfill(self, since_id=None, max_id=None, count=None):
        """ Backfill a Twitter feed.

        There are two distinct backfill processes:

        - backfill a stream if we missed items.
        - rewind a stream history until it started or until we reach
          ``config.TWITTER_BACKFILL_ALLOWED_REWIND_RANGE``; the first
          that matches stops us.

        .. note:: this method is available as a celery task
            via :func:`twitterfeed_backfill_task`.
        """

        # Going backward:
        #   - since feed creation date ?
        #   - since now ?
        #   - …
        #
        # We've got config.TWITTER_BACKFILL_ALLOWED_REWIND_RANGE.
        #
        # if self.is_backfilled:
        #     r = api.request('search/tweets', {'q': SEARCH_TERM})

        max_rewind_range = config.TWITTER_BACKFILL_ALLOWED_REWIND_RANGE

        parameters = {}

        if since_id is None and max_id is None:
            # This is the “backfill history” call. See if we are already
            # done, else do a full backfill until start of stream is
            # reached on the Twitter side, or max_rewind_range locally.
            if self.backfill_completed == 0 \
                or max_rewind_range > 0 \
                    and self.backfill_completed >= max_rewind_range:
                LOGGER.info(u'%s: backfill already completed, aborting.', self)
                return

            latest_id = self.latest_id
            oldest_id = self.oldest_id

            if oldest_id is None:
                if latest_id is not None:
                    # We never backfilled before, but already got some data.
                    oldest_id = self.items.tweet().order_by(
                        'Tweet___tweet_id').first().tweet_id

                    # BTW, store it.
                    self.set_oldest_id(oldest_id)

                    # We don't use since_id (even not "1"). We will rewind
                    # slowly from (now) present to past. Using 1 would make
                    # us begin at stream start, which seems less relevant
                    # for me, because more recent data is more important to
                    # my eye. We “- 1” because
                    # https://dev.twitter.com/rest/public/timelines
                    max_id = oldest_id - 1

        if since_id:
            parameters['since_id'] = since_id

        if max_id:
            parameters['max_id'] = max_id

        # —————————————————————————————————————————————— The backfill operation

        if since_id or max_id:
            LOGGER.info(u'%s: backfilling since %s to max %s…',
                        self, since_id, max_id)

        else:
            # We never got any item from this stream.
            # Who called us ??? It was too early.
            LOGGER.info(u'%s: Backfilling for first '
                        u'content in the feed.', self)

        # can be None
        period_start_item = self.oldest_id

        try:
            if self.is_timeline:
                # WARNING: statuses/home_timeline API 15 per 15 minute only…

                parameters.update({
                    'count': count or 200,  # Else it's 20 by default…
                    'trim_user': 1,
                })

                self.__consume_items('statuses/home_timeline',
                                     parameters, backfilling=True)

            elif self.uri:
                # We have a twitter list.
                owner_screen_name, _, slug = self.uri[1:].split(u'/')

                parameters.update({
                    'count': count or 200,  # Else it's 20 by default…
                    'include_rts': 1,
                    'slug': slug,
                    'owner_screen_name': owner_screen_name
                })

                self.__consume_items('lists/statuses',
                                     parameters, backfilling=True)

            elif self.track_terms or self.track_locations:

                parameters.update({
                    'count': count or 200,  # Else it's 20 by default…
                    'result_type': 'recent',  # or: 'mixed', 'popular'
                })

                if self.track_terms:
                    parameters['track'] = self.track_terms

                if self.track_locations:
                    parameters['locations'] = self.track_locations

                # Search/tweets doesn't use locations (bounding boxes),
                # but geocodes (bounding circles)… We need to convert,
                # and results won't be exactly the same.
                # Geocode: 37.781157,-122.398720,1mi

                self.__consume_items('search/tweets',
                                     parameters, backfilling=True)

        finally:
            self.check_new_good_period(period_start_item, self.oldest_id)


# ———————————————————————————————————————————————————————————————— Celery tasks

register_task_method(TwitterFeed, TwitterFeed.backfill,
                     globals(), queue=u'permanent')

register_task_method(TwitterFeed, TwitterFeed.consume,
                     globals(), queue=u'permanent')

# ————————————————————————————————————————————————————————————————————— Signals
#
# HEADS UP: see subscription.py for other signals.
#


def twitterfeed_pre_save(instance, **kwargs):
    """ Update owner's subscription name when twitterfeed name changes. """

    twitterfeed = instance

    # 12 is for a max of 180 API calls per 15 minutes.
    twitterfeed.fetch_interval = max(12, config.TWITTER_FEEDS_RELAUNCH_INTERVAL)

    if not twitterfeed.pk:
        # The feed is beeing created.
        # The subscription doesn't exist yet.
        return

    if 'name' in twitterfeed.changed_fields:
        # Push the name update from the twitterfeed
        # to the owner's corresponding subscription.
        #
        # HEADS UP: we use filter()/update(), and not get()
        # even if are sure there is only one subscription,
        # to avoid a post_save() signal loop.
        #
        # TODO: refactor/merge this in BaseFeed, with a test
        # on feed.user to avoid crashing on feeds types other
        # than twitter/mail that are user-created.
        twitterfeed.subscriptions.filter(
            user=twitterfeed.user).update(name=twitterfeed.name)


def twitterfeed_post_save(instance, **kwargs):

    if kwargs.get('created', False):
        statsd.gauge('feeds.counts.twitter', 1, delta=True)


def twitterfeed_pre_delete(instance, **kwargs):

    statsd.gauge('feeds.counts.twitter', -1, delta=True)


# Because http://stackoverflow.com/a/24624838/654755 doesn't work.
pre_save.connect(basefeed_pre_save, sender=TwitterFeed)

pre_save.connect(twitterfeed_pre_save, sender=TwitterFeed)
post_save.connect(twitterfeed_post_save, sender=TwitterFeed)
pre_delete.connect(twitterfeed_pre_delete, sender=TwitterFeed)
