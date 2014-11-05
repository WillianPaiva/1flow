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

    'usercounters_all_articles_count_default',
    'usercounters_unread_articles_count_default',
    'usercounters_starred_articles_count_default',
    'usercounters_bookmarked_articles_count_default',
    'usercounters_archived_articles_count_default',

    'usercounters_fun_articles_count_default',
    'usercounters_fact_articles_count_default',
    'usercounters_number_articles_count_default',
    'usercounters_analysis_articles_count_default',
    'usercounters_quote_articles_count_default',
    'usercounters_knowhow_articles_count_default',
    'usercounters_rules_articles_count_default',
    'usercounters_prospective_articles_count_default',
    'usercounters_knowledge_articles_count_default',

]

# —————————————————————————————————————————————————————— Redis counters helpers


def usercounters_all_articles_count_default(user_counters):

    return user_counters.user.reads.count()


def usercounters_unread_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_read__ne=True).count()


def usercounters_starred_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_starred=True).count()


def usercounters_archived_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_archived=True).count()


def usercounters_bookmarked_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_bookmarked=True).count()


def usercounters_fact_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_fact=True).count()


def usercounters_number_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_number=True).count()


def usercounters_analysis_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_analysis=True).count()


def usercounters_quote_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_quote=True).count()


def usercounters_prospective_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_prospective=True).count()


def usercounters_knowhow_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_knowhow=True).count()


def usercounters_knowledge_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_knowledge=True).count()


def usercounters_rules_articles_count_default(user_counters):

    return user_counters.user.reads.filter(is_rules=True).count()


def usercounters_fun_articles_count_default(user_counters):

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

    all_articles_count = IntRedisDescriptor(
        attr_name='uc.aa_c', field_name='user_id',
        default=usercounters_all_articles_count_default,
        set_default=True, min_value=0)

    unread_articles_count = IntRedisDescriptor(
        attr_name='uc.ua_c', field_name='user_id',
        default=usercounters_unread_articles_count_default,
        set_default=True, min_value=0)

    starred_articles_count = IntRedisDescriptor(
        attr_name='uc.sa_c', field_name='user_id',
        default=usercounters_starred_articles_count_default,
        set_default=True, min_value=0)

    archived_articles_count = IntRedisDescriptor(
        attr_name='uc.ra_c', field_name='user_id',
        default=usercounters_archived_articles_count_default,
        set_default=True, min_value=0)

    bookmarked_articles_count = IntRedisDescriptor(
        attr_name='uc.ba_c', field_name='user_id',
        default=usercounters_bookmarked_articles_count_default,
        set_default=True, min_value=0)

    # ————————————————————————————————————————— Watch attributes Redis counters

    fact_articles_count = IntRedisDescriptor(
        attr_name='uc.fa_c', field_name='user_id',
        default=usercounters_fact_articles_count_default,
        set_default=True, min_value=0)

    number_articles_count = IntRedisDescriptor(
        attr_name='uc.na_c', field_name='user_id',
        default=usercounters_number_articles_count_default,
        set_default=True, min_value=0)

    analysis_articles_count = IntRedisDescriptor(
        attr_name='uc.ya_c', field_name='user_id',
        default=usercounters_analysis_articles_count_default,
        set_default=True, min_value=0)

    quote_articles_count = IntRedisDescriptor(
        attr_name='uc.qa_c', field_name='user_id',
        default=usercounters_quote_articles_count_default,
        set_default=True, min_value=0)

    prospective_articles_count = IntRedisDescriptor(
        attr_name='uc.pa_c', field_name='user_id',
        default=usercounters_prospective_articles_count_default,
        set_default=True, min_value=0)

    rules_articles_count = IntRedisDescriptor(
        attr_name='uc.ra_c', field_name='user_id',
        default=usercounters_rules_articles_count_default,
        set_default=True, min_value=0)

    knowhow_articles_count = IntRedisDescriptor(
        attr_name='uc.ka_c', field_name='user_id',
        default=usercounters_knowhow_articles_count_default,
        set_default=True, min_value=0)

    knowledge_articles_count = IntRedisDescriptor(
        attr_name='uc.oa_c', field_name='user_id',
        default=usercounters_knowledge_articles_count_default,
        set_default=True, min_value=0)

    fun_articles_count = IntRedisDescriptor(
        attr_name='uc.la_c', field_name='user_id',
        default=usercounters_fun_articles_count_default,
        set_default=True, min_value=0)

    # —————————————————————————————————————————————————————— Django & Grappelli

    def __unicode__(self):
        return _(u'Counters for user {0})').format(
            self.user.username)


# ————————————————————————————————————————————————————————————————————— Signals


def user_post_save(instance, **kwargs):
    """ Create the UserFeeds set. """

    user = instance

    if kwargs.get('created', False):

        user_counters = UserCounters(user=user)
        user_counters.save()

post_save.connect(user_post_save, sender=User)
