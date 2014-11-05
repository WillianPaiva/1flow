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
from ..subscription import Subscription, subscribe_user_to_feed

LOGGER = logging.getLogger(__name__)

__all__ = [
    'UserSubscriptions',
]


# ——————————————————————————————————————————————————————————————————————— Model


class UserSubscriptions(models.Model):

    """ A set of subscriptions to factory feeds for each user. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'User subscriptions')
        verbose_name_plural = _(u'Users subscriptions')

    user = models.OneToOneField(
        User,
        related_name='user_subscriptions',
        primary_key=True)

    imported_items = models.OneToOneField(
        Subscription, null=True, blank=True,
        verbose_name=_(u'Web import subscription'),
        related_name='imported_items_user_subscriptions')

    sent_items = models.OneToOneField(
        Subscription, null=True, blank=True,
        verbose_name=_(u'Sent items subscription'),
        related_name='sent_items_user_subscriptions')

    received_items = models.OneToOneField(
        Subscription, null=True, blank=True,
        verbose_name=_(u'Received items subscription'),
        related_name='received_items_user_subscriptions')

    # The union of all blogs
    written_items = models.OneToOneField(
        Subscription, null=True, blank=True,
        verbose_name=_(u'Written items subscription'),
        related_name='written_items_user_subscriptions')

    blogs = models.ManyToManyField(Subscription, null=True, blank=True,
                                   verbose_name=_(u'User blogs'),
                                   related_name='blogs')

    # —————————————————————————————————————————————————————— Django & Grappelli

    def __unicode__(self):
        return _(u'Internal subscriptions for user {0})').format(
            self.user.username)

    @property
    def all_ids(self):
        """ Return IDs of all user subscriptions.

        .. note:: keep in sync between user/feeds.py & user/subscriptions.py
        """
        return [
            self.imported_items_id,
            self.sent_items_id,
            self.received_items_id,
            self.written_items_id,
        ] + list(self.blogs.all().values_list('id', flat=True))

    def all(self):
        """ Return a QS of all user subscriptions.

        .. note:: keep in sync between user/feeds.py & user/subscriptions.py
        """
        return Subscription.objects.filter(id__in=[
            self.imported_items_id,
            self.sent_items_id,
            self.received_items_id,
            self.written_items_id
        ]) | self.blogs.all()

    def check(self, force=False):
        """ Create user feeds if they don't already exist. """

        needs_save = False

        user = self.user

        # Be sure all feeds exist before trying to link to them.
        user.user_feeds.check()

        for feed_key_name, data in SPECIAL_FEEDS_DATA.items():

            # LOGGER.debug(u'Sub %s is %s', feed_key_name,
            #              getattr(self, feed_key_name + '_id'))

            if getattr(self, feed_key_name + '_id') is None:

                url, tmpl_name = data

                subscription = subscribe_user_to_feed(
                    user=user,
                    feed=getattr(user.user_feeds, feed_key_name),
                    name=tmpl_name.format(user.username),

                    # In case the feed has already articles,
                    # check in the background to avoid waiting.
                    background=True,
                )

                setattr(self, feed_key_name, subscription)

                needs_save = True

        if needs_save:
            self.save()


# ————————————————————————————————————————————————————————————————————— Signals


def user_post_save(instance, **kwargs):
    """ Create the UserFeeds set. """

    user = instance

    if kwargs.get('created', False):

        user_subscriptions = UserSubscriptions(user=user)
        user_subscriptions.check()

post_save.connect(user_post_save, sender=User)


# ————————————————————————————————————————————————————————— External properties
#                                            Defined here to avoid import loops
#                                           Please sync the code with userfeeds


def make_subscriptions_attr_getter(subscription_key_name):
    def attr_getter(self):
        return getattr(self.subscriptions, subscription_key_name)
    return attr_getter

for subscription_key_name in SPECIAL_FEEDS_DATA:
    setattr(User, subscription_key_name + '_subscription',
            property(make_subscriptions_attr_getter(subscription_key_name)))


def User_blogs_subscriptions_property_get(self):
    """ Return subscriptions of a user to his/her blogs. """

    return self.subscriptions.blogs


def User_standard_subscriptions_property_get(self):
    """ “standard” subscriptions, eg. not special (immutable) ones.

    .. todo:: is there a way to make a manager of this property?

    .. note:: this property has no equivalent in userfeeds, because
        “users have no feed”: there is no such a feature for a user
        to see his/her feeds, this is a non-sense.
    """

    exclude_ids = tuple(getattr(self.subscriptions, sname + '_id')
                        for sname in SPECIAL_FEEDS_DATA)

    return self.subscription_set.exclude(id__in=exclude_ids)

    # For memories, the MongoDB equivalent.
    # return self.all_subscriptions(feed__nin=[self.web_import_feed,
    #                                          self.sent_items_feed,
    #                                          self.received_items_feed])


User.blogs_subscriptions    = property(User_blogs_subscriptions_property_get)
User.standard_subscriptions = property(User_standard_subscriptions_property_get)
