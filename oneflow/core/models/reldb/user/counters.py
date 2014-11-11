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
from oneflow.base.fields import IntRedisDescriptor

from ..common import DjangoUser as User

LOGGER = logging.getLogger(__name__)

__all__ = [
    'UserCounters',

    'usercounters_all_items_count_default',
    'usercounters_unread_items_count_default',
    'usercounters_starred_items_count_default',
    'usercounters_bookmarked_items_count_default',
    'usercounters_archived_items_count_default',

    'usercounters_fun_items_count_default',
    'usercounters_fact_items_count_default',
    'usercounters_number_items_count_default',
    'usercounters_analysis_items_count_default',
    'usercounters_quote_items_count_default',
    'usercounters_knowhow_items_count_default',
    'usercounters_rules_items_count_default',
    'usercounters_prospective_items_count_default',
    'usercounters_knowledge_items_count_default',

]

# —————————————————————————————————————————————————————— Redis counters helpers


def usercounters_all_items_count_default(user_counters):

    return user_counters.user.reads.count()


def usercounters_unread_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_read=False).count()


def usercounters_starred_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_starred=True).count()


def usercounters_archived_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_archived=True).count()


def usercounters_bookmarked_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_bookmarked=True).count()


def usercounters_fact_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_fact=True).count()


def usercounters_number_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_number=True).count()


def usercounters_analysis_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_analysis=True).count()


def usercounters_quote_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_quote=True).count()


def usercounters_prospective_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_prospective=True).count()


def usercounters_knowhow_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_knowhow=True).count()


def usercounters_knowledge_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_knowledge=True).count()


def usercounters_rules_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_rules=True).count()


def usercounters_fun_items_count_default(user_counters):

    return user_counters.user.reads.filter(is_fun=True).count()


# ——————————————————————————————————————————————————————————————————————— Model


class UserCounters(models.Model):

    """ A set of subscriptions to factory feeds for each user. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'User counters')
        verbose_name_plural = _(u'Users counters')

    user = models.OneToOneField(
        User,
        related_name='user_counters',
        primary_key=True)

    placeholder = models.IntegerField(
        null=True, blank=True,
        help_text=_(u'This field is here just for the model to be '
                    u'created by south/django.'))

    # —————————————————————————————————————————————————————————— Redis counters

    all_items_count = IntRedisDescriptor(
        attr_name='u.ai_c', field_name='user_id',
        default=usercounters_all_items_count_default,
        set_default=True, min_value=0)

    unread_items_count = IntRedisDescriptor(
        attr_name='u.ui_c', field_name='user_id',
        default=usercounters_unread_items_count_default,
        set_default=True, min_value=0)

    starred_items_count = IntRedisDescriptor(
        attr_name='u.si_c', field_name='user_id',
        default=usercounters_starred_items_count_default,
        set_default=True, min_value=0)

    archived_items_count = IntRedisDescriptor(
        attr_name='u.ri_c', field_name='user_id',
        default=usercounters_archived_items_count_default,
        set_default=True, min_value=0)

    bookmarked_items_count = IntRedisDescriptor(
        attr_name='u.bi_c', field_name='user_id',
        default=usercounters_bookmarked_items_count_default,
        set_default=True, min_value=0)

    # ————————————————————————————————————————— Watch attributes Redis counters

    fact_items_count = IntRedisDescriptor(
        attr_name='u.fi_c', field_name='user_id',
        default=usercounters_fact_items_count_default,
        set_default=True, min_value=0)

    number_items_count = IntRedisDescriptor(
        attr_name='u.ni_c', field_name='user_id',
        default=usercounters_number_items_count_default,
        set_default=True, min_value=0)

    analysis_items_count = IntRedisDescriptor(
        attr_name='u.yi_c', field_name='user_id',
        default=usercounters_analysis_items_count_default,
        set_default=True, min_value=0)

    quote_items_count = IntRedisDescriptor(
        attr_name='u.qi_c', field_name='user_id',
        default=usercounters_quote_items_count_default,
        set_default=True, min_value=0)

    prospective_items_count = IntRedisDescriptor(
        attr_name='u.pi_c', field_name='user_id',
        default=usercounters_prospective_items_count_default,
        set_default=True, min_value=0)

    rules_items_count = IntRedisDescriptor(
        attr_name='u.ri_c', field_name='user_id',
        default=usercounters_rules_items_count_default,
        set_default=True, min_value=0)

    knowhow_items_count = IntRedisDescriptor(
        attr_name='u.ki_c', field_name='user_id',
        default=usercounters_knowhow_items_count_default,
        set_default=True, min_value=0)

    knowledge_items_count = IntRedisDescriptor(
        attr_name='u.oi_c', field_name='user_id',
        default=usercounters_knowledge_items_count_default,
        set_default=True, min_value=0)

    fun_items_count = IntRedisDescriptor(
        attr_name='u.li_c', field_name='user_id',
        default=usercounters_fun_items_count_default,
        set_default=True, min_value=0)

    # —————————————————————————————————————————————————————— Django & Grappelli

    def __unicode__(self):
        return _(u'Counters for user {0})').format(
            self.user.username)

    def compute_cached_descriptors(self, **kwargs):

        self.all_items_count = \
            usercounters_all_items_count_default(self)

        self.unread_items_count = \
            usercounters_unread_items_count_default(self)

        self.starred_items_count = \
            usercounters_starred_items_count_default(self)

        self.archived_items_count = \
            usercounters_archived_items_count_default(self)

        self.bookmarked_items_count = \
            usercounters_bookmarked_items_count_default(self)

        self.fact_items_count = \
            usercounters_fact_items_count_default(self)

        self.number_items_count = \
            usercounters_number_items_count_default(self)

        self.analysis_items_count = \
            usercounters_analysis_items_count_default(self)

        self.quote_items_count = \
            usercounters_quote_items_count_default(self)

        self.prospective_items_count = \
            usercounters_prospective_items_count_default(self)

        self.rules_items_count = \
            usercounters_rules_items_count_default(self)

        self.knowhow_items_count = \
            usercounters_knowhow_items_count_default(self)

        self.knowledge_items_count = \
            usercounters_knowledge_items_count_default(self)

        self.fun_items_count = \
            usercounters_fun_items_count_default(self)


# ————————————————————————————————————————————————————————————————————— Signals


def user_post_save(instance, **kwargs):
    """ Create the UserFeeds set. """

    user = instance

    if kwargs.get('created', False):

        user_counters = UserCounters(user=user)
        user_counters.save()

post_save.connect(user_post_save, sender=User)
