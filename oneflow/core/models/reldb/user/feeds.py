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
import logging

# from constance import config

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save  # , pre_save, pre_delete

# from oneflow.base.utils import register_task_method

from ..common import DjangoUser as User, SPECIAL_FEEDS_DATA
from ..feed.base import BaseFeed

LOGGER = logging.getLogger(__name__)

__all__ = [
    'UserFeeds',
]


# ——————————————————————————————————————————————————————————————————————— Model


class UserFeeds(models.Model):

    """ A set of factory feeds for each user. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'User feed')
        verbose_name_plural = _(u'Users feeds')

    user = models.OneToOneField(
        User,
        related_name='user_feeds',
        primary_key=True)

    imported_items = models.ForeignKey(
        BaseFeed, null=True, blank=True,
        verbose_name=_(u'Web import feed'),
        related_name='imported_items_feeds')

    sent_items = models.ForeignKey(
        BaseFeed, null=True, blank=True,
        verbose_name=_(u'Sent items feed'),
        related_name='sent_items_feeds')

    received_items = models.ForeignKey(
        BaseFeed, null=True, blank=True,
        verbose_name=_(u'Received items feed'),
        related_name='received_items_feeds')

    # The union of all blogs
    written_items = models.ForeignKey(
        BaseFeed, null=True, blank=True,
        verbose_name=_(u'Written items feed'),
        related_name='written_items_feeds')

    blogs = models.ManyToManyField(BaseFeed, null=True, blank=True,
                                   verbose_name=_(u'User blogs'))

    # —————————————————————————————————————————————————————— Django & Grappelli

    def __unicode__(self):
        return _(u'Internal feeds for user {0})').format(self.user.username)

    def check(self, force=False):
        """ Create user feeds if they don't already exist. """

        needs_save = False

        for feed_key_name, data in SPECIAL_FEEDS_DATA.items():

            # LOGGER.debug(u'%s is %s', feed_key_name,
            #              getattr(self, feed_key_name + '_id'))

            if getattr(self, feed_key_name + '_id') is None:

                url, tmpl_name = data

                feed = BaseFeed(
                    name=tmpl_name.format(self.user.username),
                    is_restricted=True,
                    is_internal=True,
                    is_active=True,
                    is_good=True,
                )
                feed.save()

                setattr(self, feed_key_name, feed)

                needs_save = True

        if needs_save:
            self.save()


# ————————————————————————————————————————————————————————————————————— Signals


def user_post_save(instance, **kwargs):
    """ Create the UserFeeds set. """

    user = instance

    if kwargs.get('created', False):

        user_feeds = UserFeeds(user=user)
        user_feeds.check()

post_save.connect(user_post_save, sender=User)


# ————————————————————————————————————————————————————————— External properties
#                                            Defined here to avoid import loops
#                                   Please sync the code with usersubscriptions


def make_feeds_attr_getter(feed_key_name):
    def attr_getter(self):
        return getattr(self.feeds, feed_key_name)
    return attr_getter

for feed_key_name in SPECIAL_FEEDS_DATA:
    setattr(User, feed_key_name + '_feed',
            property(make_feeds_attr_getter(feed_key_name)))


def User_blogs_feeds_property_get(self):
    """ Return all blog feeds of a user. """

    return self.feeds.blogs


User.blogs_feeds = property(User_blogs_feeds_property_get)
