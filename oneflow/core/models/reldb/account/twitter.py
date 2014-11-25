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

import json
import logging

# from datetime import datetime
from constance import config
from TwitterAPI import TwitterAPI
from async_messages import message_user

from django.conf import settings
from django.db import models, IntegrityError
from django.db.models.signals import post_save, pre_save  # , pre_delete
from django.utils.translation import ugettext, ugettext_lazy as _
from django.contrib.messages import constants

from social.apps.django_app.default.models import UserSocialAuth

from oneflow.base.fields import TextRedisDescriptor
from oneflow.base.utils import register_task_method

# from oneflow.base.utils.dateutils import now
from sparks.foundations.classes import SimpleObject

from ..common import REDIS

from ..folder import Folder

# from common import TWITTER_LISTS_STRING_SEPARATOR

from base import (
    BaseAccountQuerySet,
    BaseAccountManager,
    BaseAccount,
)
LOGGER = logging.getLogger(__name__)

__all__ = [
    'TwitterAccount',
    'twitteraccount_lists_default',
]


def twitter_list_slug_from_uri(uri):
    """ Given a twitter list URI, return only the list slug. """

    return uri.rsplit('/', 1)[-1]


def twitteraccount_lists_default(twitteraccount):
    """ Build a TwitterAccount lists default value. """

    try:
        return twitteraccount.twitter_list_lists(as_text=True)

    except:
        LOGGER.exception(u'Unable to enumerate Twitter lists for account %s',
                         twitteraccount)
        return u''


# —————————————————————————————————————————————————————————— Manager / QuerySet


def BaseAccountQuerySet_twitter_method(self):
    """ Patch BaseAccountQuerySet to know how to return Twitter accounts. """

    return self.instance_of(TwitterAccount)

BaseAccountQuerySet.twitter = BaseAccountQuerySet_twitter_method


# ——————————————————————————————————————————————————————————————————————— Model


class TwitterAccount(BaseAccount):

    """ 1flow users can associate many twitter accounts to their 1flow account.

    1flow create feeds from these twitter accounts, with or without rules.
    """

    class Meta:
        app_label    = 'core'
        verbose_name = _(u'Twitter account')
        verbose_name_plural = _(u'Twitter accounts')
        # unique_together = ('user', 'username', )

    INPLACEEDIT_EXCLUDE = ('errors', 'options', )

    objects = BaseAccountManager()

    social_auth = models.OneToOneField(UserSocialAuth,
                                       verbose_name=_(u'Social account'),
                                       related_name='twitter_account')

    fetch_owned_lists = models.NullBooleanField(
        verbose_name=_(u'Fetch owned lists'),
        null=True, blank=True,
        help_text=_(u'Automatically follow the account lists, creating a '
                    u'feed with default parameters for each of them. You '
                    u'can adjust each list parameters afterwise.')
    )

    fetch_subscribed_lists = models.NullBooleanField(
        verbose_name=_(u'Fetch subscribed lists'),
        null=True, blank=True,
        help_text=_(u'Automatically follow the account lists, creating a '
                    u'feed with default parameters for each of them. You '
                    u'can adjust each list parameters afterwise.')
    )

    timeline = models.OneToOneField(
        'TwitterFeed',
        null=True, blank=True,
        verbose_name=_(u'Timeline'),
        help_text=_(u'Account timeline'),
        related_name='twitter_account'
    )

    # retweets = OneToOneField('TwitterFeed',
    #   verbose_name=_(u'Retweets'),
    #   help_text=_(u'What you have retweeted from others'))
    # favs = OneToOneField('TwitterFeed',
    #   verbose_name=_(u'Favorites'),
    #   help_text=_(u'What your have favorited from others'))
    # dms = OneToOneField('TwitterFeed',
    #   verbose_name=_(u'Direct messages'),
    #   help_text=_(u'Direct messages from others & to others'))
    # retweeted = OneToOneField('TwitterFeed',
    #   verbose_name=_(u'Retweeted tweets'),
    #   help_text=_(u'Tweets from you that other retweeted'))
    # favorited = OneToOneField('TwitterFeed',
    #   verbose_name=_(u'Favorited tweets (by other)'),
    #   help_text=_(u'Tweets from you that other favorited'))

    _lists_ = TextRedisDescriptor(
        attr_name='ta.ls', default=twitteraccount_lists_default,
        set_default=True)

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def check_social_user(cls, social_user, **kwargs):

        LOGGER.warning(u'Check social user %s', social_user)

        if not social_user.provider == 'twitter':
            return

        try:
            social_user.twitter_account

        except TwitterAccount.DoesNotExist:

            twitter_account = TwitterAccount(user=social_user.user,
                                             social_auth=social_user)
            twitter_account.save()

        globals['twitteraccount_check_feeds_task'].delay(twitter_account.id)

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def lists(self):
        """ Return a list of lists of the account.

        If it was refreshed too long in the past, rebuild the list.
        """
        _lists_ = self._lists_

        # LOGGER.debug(u'%s: lists are %s in Redis.',
        #              self, _lists_)

        if not self.recently_usable or not _lists_:
            # HEADS UP: this task name will be registered later
            # by the register_task_method() call.
            globals()['twitteraccount_update_lists_task'].delay(self.id)

        lists = self._build_self_lists_object()

        if not _lists_:
            return lists

        json_lists = json.loads(_lists_)

        lists.owned = json_lists['owned']
        lists.subscribed = json_lists['subscribed']

        return lists

    @property
    def redis_lists_key(self):
        """ Return a unique key for the current account lists (redis hash). """

        return u'ta:{0}:l'.format(self.id)

    @property
    def twitter_folder(self):

        base_folder, created = Folder.add_folder(
            name=ugettext(u'Twitter streams'),
            user=self.user)

        if not base_folder.image_url:
            base_folder.image_url = \
                u'/static/icon-themes/Faenza/apps/96/twitter.png'
            base_folder.save()

        return base_folder

    @property
    def config_account_refresh_period(self):
        """ Return the Twitter account refresh period. """

        return config.TWITTER_ACCOUNT_REFRESH_PERIOD

    # —————————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        """ OMG, that's __unicode__, pep257. """

        return u'Twitter account “{0}” of user {1}'.format(
            self.name, self.user
        )

    # —————————————————————————————————————————————————————————————————— Python

    def __enter__(self, *args, **kwargs):

        # https://dev.twitter.com/streaming/reference/get/user
        # https://dev.twitter.com/overview/api/response-codes

        if not hasattr(self, '_tweetapi_') or self._tweetapi_ is None:

            if settings.DEBUG or settings.SITE_DOMAIN in ('lil.1flow.io',
                                                          'big.1flow.io', ):
                self._tweetapi_ = TwitterAPI(
                    settings.SOCIAL_AUTH_TWITTER_KEY,
                    settings.SOCIAL_AUTH_TWITTER_SECRET,
                    '1119347214-bdMoepqko61yWiQ9BMKeTMNWI0LwhQweOD8P7A1',
                    'OyJ3KzCej9MZRMXML4iLsoebUykQOIcr8BDa8USqKxO0K')

            else:
                raise NotImplementedError(
                    u'Not implemented until '
                    u'https://github.com/omab/python-social-auth/issues/444 is resolved.')  # NOQA

                access_token_key, access_token_secret = \
                    self.social_auth.tokens.split('&')

                self._tweetapi_ = TwitterAPI(
                    settings.SOCIAL_AUTH_TWITTER_KEY,
                    settings.SOCIAL_AUTH_TWITTER_SECRET,
                    access_token_key,
                    access_token_secret)

        return self._tweetapi_

    def __exit__(self, e_typ, e_val, trcbak):

        if hasattr(self, '_tweetapi_') \
                and self._tweetapi_ is not None:

            self._tweetapi_ = None

        # if all((e_typ, e_val, trcbak)):
        #    raise e_typ, e_val, trcbak

    # ——————————————————————————————————————————————————————————————— Internals

    def clear_cache(self):
        """ Clear all the account caches. """

        self._redis_clear_cache()

    def _redis_clear_cache(self):
        """ Clears the account's Redis cache. """

        REDIS.delete(self.redis_lists_key)

        LOGGER.info(u'%s: cleared redis cache. Happy downloading…',
                    self)

    def _build_self_lists_object(self):

        lists = SimpleObject()
        lists.owned = []
        lists.subscribed = []

        return lists

    def set_list(self, twitter_list):
        """ Store a list in our redis slot. """

        REDIS.hset(self.redis_lists_key,
                   twitter_list['uri'],
                   json.dumps(twitter_list))

        return twitter_list['uri']

    def get_list(self, list_uri):

        result = REDIS.hget(self.redis_lists_key, list_uri)

        if result is None:
            twitter_list = self.twitter_get_lists_show(list_uri)

            if twitter_list:
                self.set_list(twitter_list)
                result = twitter_list

        else:
            result = json.loads(result)

        return result

    def twitter_get_lists_show(self, list_name):
        """ Get a list from twitter lists/show API and update the cache. """

        # Skip leading '/' when splitting
        owner_screen_name, _, slug = list_name[1:].split(u'/')

        with self as tweetapi:
            result = tweetapi.request('lists/show', {
                'slug': slug, 'owner_screen_name': owner_screen_name
            })

            return result.json()

    def check_feeds(self, force=False, commit=True):
        """ Check the twitter account timeline is a 1flow feed. """

        # Avoid circular import
        from ..feed.twitter import TwitterFeed
        from ..subscription import subscribe_user_to_feed

        if self.timeline is None:

            # TODO: merge this with
            #       self._create_feed_from_list_and_subscribe_to_it()
            #       only the get_list() and the is_timeline differ.

            username = self.social_auth.extra_data.get(
                'username', self.social_auth.uid)

            timeline = TwitterFeed(
                user=self.user,
                name=_(u'Twitter timeline for @{0}').format(username),
                is_timeline=True,
                is_backfilled=True,
                id_good=True,
            )

            timeline.save()

            # Mandatory to check the timeline of this SOLE
            # account, and to be able to get it back afterwise.
            timeline.account.add(self)

            self.timeline = timeline
            self.save()

            LOGGER.info(u'%s: created timeline feed %s.',
                        self, self.timeline)

            message_user(
                self.user,
                _(u'Subscribed you to @{0}\'s Twitter timeline.').format(
                    username),
                constants.SUCCESS)

        timeline_subscription = subscribe_user_to_feed(user=self.user,
                                                       feed=self.timeline)

        if not timeline_subscription.folders.exists():
            timeline_subscription.folders.add(self.twitter_folder)

        self.check_lists(force=force, commit=commit)

    def _create_feed_from_list_and_subscribe_to_it(self, list_name):
        """ Create a 1flow feed and subscribe account owner to it.


        :param twitter_list: a Twitter list name, as used as unique ID
            accross the 1flow twitter account model.

        .. note:: this is an internal method, not meant to be used from
            the outside. It implements no checks at all.
        """

        # Avoid circular import
        from ..feed.twitter import TwitterFeed
        from ..subscription import subscribe_user_to_feed

        twitter_list = self.get_list(list_name)

        if twitter_list is None:
            LOGGER.warning(u'%s: could not get list %s',
                           self, list_name)
            return None, None, None

        return_value = False

        twitter_feed = TwitterFeed(
            user=self.user,
            name=_(u'Twitter list “{0}”').format(
                twitter_list['name']),
            uri=twitter_list['uri'],
            is_timeline=False,
            is_backfilled=config.TWITTER_FEEDS_DEFAULT_BACKFILL,
            is_good=True,
        )

        try:
            twitter_feed.save()

        except IntegrityError:

            # TODO: check attributes have good values…
            #       for example if TWITTER_FEEDS_DEFAULT_BACKFILL
            #       changed…

            twitter_feed = TwitterFeed.objects.get(
                user=self.user, uri=twitter_list['uri'])

            if not twitter_feed.is_active:
                twitter_feed.reopen(u'Owner re-subscribed to list from '
                                    u'Twitter account (system processing).')

        else:
            return_value = True

        subscription = subscribe_user_to_feed(user=self.user,
                                              feed=twitter_feed)

        if not subscription.folders.exists():
            subscription.folders.add(self.twitter_folder)

        return twitter_feed, subscription, return_value

    def check_lists(self, force=False, commit=True):
        """ Check Twitter account's lists are local 1flow feeds.

        Local twitter feeds will be created if constance config or user
        preferences say so, and existing local feeds will be deleted if
        present but the local user doesn't want them anymore.
        """

        # https://dev.twitter.com/rest/reference/get/lists/subscriptions

        #
        # TODO: the deletion process is overkill: it will create
        #       subscriptions to delete them afterwards. We should
        #       optimize. But BTW, creating [closed] feeds for all
        #       lists seems a good thing, at first sight.
        #

        lists = self.lists

        if lists is None:
            LOGGER.warning(u'Lists are outdated or inexistant. '
                           u'Please refresh them first (the task '
                           u'should be already underway).')
            return

        created_lists = []
        deleted_lists = []

        if self.fetch_owned_lists:
            for list_name in lists.owned:
                feed, subscription, created = \
                    self._create_feed_from_list_and_subscribe_to_it(
                        list_name)

                if created:
                    created_lists.append(list_name)

        else:
            for list_name in lists.owned:
                feed, subscription, created = \
                    self._create_feed_from_list_and_subscribe_to_it(
                        list_name)

                feed.close(u'Owner does not fetch owned lists anymore')
                subscription.delete()

                deleted_lists.append(list_name)

        if self.fetch_subscribed_lists:
            for list_name in lists.subscribed:
                feed, subscription, created = \
                    self._create_feed_from_list_and_subscribe_to_it(
                        list_name)

                if created:
                    created_lists.append(list_name)
        else:
            for list_name in lists.subscribed:
                feed, subscription, created = \
                    self._create_feed_from_list_and_subscribe_to_it(
                        list_name)

                feed.close(u'Owner does not fetch subscribed lists anymore')
                subscription.delete()

                deleted_lists.append(list_name)

        tlsfu = twitter_list_slug_from_uri

        if created_lists:
            message_user(
                self.user,
                _(u'Subscribed you to {0} Twitter list(s): {1}.').format(
                    len(created_lists), u', '.join(
                        tlsfu(l) for l in created_lists)),
                constants.SUCCESS)

        if deleted_lists:

            # Given the way checks work, don't bother the user with messages
            # he/she didn't asked for. Eg. if lists fetching is disabled, no
            # need to tell him/her he/she is unsubscribed, because he/she
            # should already be.
            if config.TWITTER_ACCOUNT_FETCH_OWNED_LISTS \
                    or config.TWITTER_ACCOUNT_FETCH_SUBSCRIBED_LISTS:
                message_user(
                    self.user,
                    _(u'Unsubscribed from {0} Twitter list(s): {1}.').format(
                        len(deleted_lists), u', '.join(
                            tlsfu(l) for l in deleted_lists)),
                    constants.INFO)

    def test_connection(self, force=False):
        """ Test connection and report any error.

        This function does everything manually and independantly,
        outside of the context processor, to be able to test
        everything eventually while anything else is already running.
        """

        # {
        #    u'always_use_https': True,
        #    u'discoverable_by_email': True,
        #    u'discoverable_by_mobile_phone': False,
        #    u'display_sensitive_media': True,
        #    u'geo_enabled': False,
        #    u'language': u'fr',
        #    u'protected': False,
        #    u'screen_name': u'1flow_io',
        #    u'sleep_time': {
        #       u'enabled': False,
        #       u'end_time': None,
        #       u'start_time': None
        #    },
        #    u'time_zone': {
        #       u'name': u'Paris',
        #       u'tzinfo_name': u'Europe/Paris',
        #       u'utc_offset': 3600
        #    },
        #    u'use_cookie_personalization': True
        # }
        #
        # https://dev.twitter.com/rest/reference/get/account/settings
        # https://dev.twitter.com/rest/reference/get/help/configuration

        if self.recently_usable and not force:
            return

        LOGGER.info(u'Testing connection of %s', self)

        with self as tweetapi:
            try:
                result = tweetapi.request('account/settings')

            except Exception, e:
                self.mark_unusable(u'Get Twitter account/settings failed',
                                   exc=e)

            else:
                dict_result = result.json()

                # {'limit': None, 'remaining': 14, 'reset': None}
                quota = result.get_rest_quota()

                self.mark_usable()

                if settings.DEBUG and 'screen_name' in dict_result:
                    message_user(
                        self.user,
                        _(u'Twitter account successfully tested (quota '
                          u'remaining: {0}).').format(quota['remaining']),
                        constants.INFO)

    def update_lists(self):
        """ Simply update the remote lists names.

        .. note:: this method is registered as a task in Celery.
        """

        if not self.recently_usable:
            return

        self._lists_ = twitteraccount_lists_default(self)

        LOGGER.debug(u'%s: Twitter lists updated; owned: %s, subscribed: %s.',
                     self, u', '.join(self.lists.owned),
                     u', '.join(self.lists.subscribed))

        return self.lists

    # ———————————————————————————————————————————————————————— Twitter wrappers

    def twitter_list_lists(self, as_text=False):
        """ List twitter lists. """

        # GET lists/ownerships
        # https://dev.twitter.com/rest/reference/get/lists/ownerships
        # GET lists/subscriptions
        # https://dev.twitter.com/rest/reference/get/lists/subscriptions
        # OR (less cool)
        # https://dev.twitter.com/rest/reference/get/lists/list
        #
        # Then:
        # https://dev.twitter.com/rest/reference/get/lists/statuses

        lists = self._build_self_lists_object()

        with self as tweetapi:

            # ————————————————————————————————————————————————————— Owned lists

            result = tweetapi.request('lists/ownerships')

            try:
                twitter_lists = result.json()['lists']

            except:
                LOGGER.exception(u'%s: could not get owned lists', self)

            else:
                for twitter_list in twitter_lists:
                    lists.owned.append(self.set_list(twitter_list))

            # ———————————————————————————————————————————————— Subscribed lists

            result = tweetapi.request('lists/subscriptions')

            try:
                twitter_lists = result.json()['lists']

            except:
                LOGGER.exception(u'%s: could not get subscribed lists', self)

            else:
                for twitter_list in twitter_lists:
                    lists.subscribed.append(self.set_list(twitter_list))

        REDIS.expire(self.redis_lists_key,
                     config.TWITTER_LISTS_CACHE_EXPIRY
                     or config.TWITTER_DEFAULT_CACHE_EXPIRY)

        # Update the last connection datetime.
        self.mark_usable(verbose=False)

        if as_text:
            return json.dumps({
                'owned': lists.owned,
                'subscribed': lists.subscribed,
            })

        return lists


# ———————————————————————————————————————————————————————————————— Celery tasks

register_task_method(TwitterAccount, TwitterAccount.check_lists,
                     globals(), queue=u'background')
register_task_method(TwitterAccount, TwitterAccount.test_connection,
                     globals(), queue=u'swarm')
register_task_method(TwitterAccount, TwitterAccount.update_lists,
                     globals(), queue=u'low')

# ————————————————————————————————————————————————————————————————————— Signals


def twitteraccount_pre_save(instance, **kwargs):

    twitter_account = instance

    if twitter_account.fetch_owned_lists is None:
        twitter_account.fetch_owned_lists = \
            config.TWITTER_ACCOUNT_FETCH_OWNED_LISTS

    if twitter_account.fetch_subscribed_lists is None:
        twitter_account.fetch_subscribed_lists = \
            config.TWITTER_ACCOUNT_FETCH_SUBSCRIBED_LISTS

    if twitter_account.name in (None, u''):

        username = twitter_account.social_auth.extra_data.get('username', None)

        if username:
            twitter_account.name = u'@{0}'.format(username)

        else:
            twitter_account.name = _(u'Twitter account #{0}').format(
                twitter_account.social_auth.uid)


def usersocialauth_post_save(instance, **kwargs):
    """ Ensure a Twitter social_auth has a 1flow twitter account.

    .. todo:: This is probably a duplicate of the social_auth pipeline
        checker function. Advise with experience / tests.
    """

    TwitterAccount.check_social_user(social_user=instance)


post_save.connect(usersocialauth_post_save, sender=UserSocialAuth)
pre_save.connect(twitteraccount_pre_save, sender=TwitterAccount)
