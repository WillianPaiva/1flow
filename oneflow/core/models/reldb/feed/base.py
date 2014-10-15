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
import uuid
import logging

from constance import config
from collections import OrderedDict
from transmeta import TransMeta
from jsonfield import JSONField

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.db.models.signals import pre_save, post_save, pre_delete

# from polymorphic import PolymorphicModel

from sparks.django.models import ModelDiffMixin

# from django.utils.translation import ugettext as _
# from django.utils.text import slugify
# from sparks.django.models import ModelDiffMixin

from oneflow.base.utils.dateutils import now

from ..common import DjangoUser  # , REDIS
from ..language import Language
# from mail_common import email_get_first_text_block

LOGGER = logging.getLogger(__name__)

__all__ = [
    'BaseFeed',

    'basefeed_all_articles_count_default',
    'basefeed_good_articles_count_default',
    'basefeed_bad_articles_count_default',
    'basefeed_recent_articles_count_default',
    'basefeed_subscriptions_count_default',
]


def get_feed_thumbnail_upload_path(instance, filename):

    if not filename.strip():
        filename = uuid.uuid4()

    # The filename will be used in a shell command later. In case the
    # user/admin forgets the '"' in the configuration, avoid problems.
    filename = filename.replace(u' ', u'_')

    if instance:
        return 'feed/{0}/thumbnails/{1}'.format(instance.id, filename)

    return u'thumbnails/%Y/%m/%d/{0}'.format(filename)


def basefeed_all_articles_count_default(feed, *args, **kwargs):

    return feed.articles.count()


def basefeed_good_articles_count_default(feed, *args, **kwargs):

    return feed.good_articles.count()


def basefeed_bad_articles_count_default(feed, *args, **kwargs):

    return feed.bad_articles.count()


def basefeed_recent_articles_count_default(feed, *args, **kwargs):

    return feed.recent_articles.count()


def basefeed_subscriptions_count_default(feed, *args, **kwargs):

    return feed.subscriptions.count()


# class BaseFeed(PolymorphicModel, ModelDiffMixin):

class BaseFeed(ModelDiffMixin):

    """ Base 1flow feed, abstract class.

    .. todo::
        created_by   → creator
        restricted   → is_restricted
        closed       → is_active
        last_fetch   → date_last_fetch
        good_for_use → is_good
        date_added   → date_created
        errors : ListField(StringField) → JSONField
    """

    __metaclass__ = TransMeta

    class Meta:
        abstract = True
        app_label = 'core'
        translate = ('short_description', 'description', )
        verbose_name = _(u'Base feed')
        verbose_name_plural = _(u'Base feeds')

    # NOTE: keep ID a simple integer/auto
    # field, this surely helps JOIN operations.
    # id             = models.UUIDField(primary_key=True,
    #                                   default=uuid.uuid4, editable=False)

    creator        = models.ForeignKey(DjangoUser, null=True, blank=True)
    name           = models.CharField(verbose_name=_(u'name'), max_length=128)
    slug           = models.CharField(verbose_name=_(u'slug'),
                                      null=True, max_length=128, blank=True)
    languages      = models.ManyToManyField(
        Language, verbose_name=_(u'Languages'),
        help_text=_(u'Set this to more than one language to help article '
                    u'language detection if none is set in articles.'))

    date_created   = models.DateTimeField(auto_now_add=True, default=now,
                                          verbose_name=_(u'date created'))
    is_internal    = models.BooleanField(verbose_name=_(u'Internal'),
                                         blank=True, default=False)
    is_restricted  = models.BooleanField(
        default=False, verbose_name=_(u'restricted'), blank=True,
        help_text=_(u'Is this feed available only to paid subscribers on its '
                    u'publisher\'s web site?'))
    is_active = models.BooleanField(
        verbose_name=_(u'active'), default=True, blank=True,
        help_text=_(u'Is the feed refreshed or dead?'))
    date_closed    = models.DateTimeField(verbose_name=_(u'date closed'),
                                          null=True, blank=True)
    closed_reason  = models.TextField(verbose_name=_(u'closed reason'),
                                      null=True, blank=True)

    fetch_interval = models.IntegerField(
        default=config.FEED_FETCH_DEFAULT_INTERVAL,
        verbose_name=_(u'fetch interval'), blank=True)
    date_last_fetch = models.DateTimeField(verbose_name=_(u'last fetch'),
                                           null=True, blank=True)

    errors         = JSONField(load_kwargs={'object_pairs_hook': OrderedDict},
                               null=True, blank=True)
    options        = JSONField(load_kwargs={'object_pairs_hook': OrderedDict},
                               null=True, blank=True)

    duplicate_of   = models.ForeignKey('self', null=True, blank=True)

    notes          = models.TextField(
        verbose_name=_(u'Notes'), null=True, blank=True,
        help_text=_(u'Internal notes for 1flow staff related to this feed.'))

    is_good = models.BooleanField(
        verbose_name=_(u'Shown in selector'), default=False,
        help_text=_(u'Make this feed available to new subscribers in the '
                    u'selector wizard. Without this, the user can still '
                    u'subscribe but he must know it and manually enter '
                    u'the feed address.'))

    thumbnail = models.ImageField(
        verbose_name=_(u'Thumbnail'), null=True, blank=True,
        upload_to=get_feed_thumbnail_upload_path,
        help_text=_(u'Use either thumbnail when 1flow instance hosts the '
                    u'image, or thumbnail_url when hosted elsewhere. If '
                    u'both are filled, thumbnail takes precedence.'))

    thumbnail_url  = models.URLField(
        verbose_name=_(u'Thumbnail URL'), null=True, blank=True,
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
