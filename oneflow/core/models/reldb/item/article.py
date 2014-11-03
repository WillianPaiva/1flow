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

import logging

import uuid

from statsd import statsd
# from constance import config

from celery import chain as tasks_chain
# from celery.exceptions import SoftTimeLimitExceeded

from humanize.time import naturaldelta
from humanize.i18n import django_language

# from django.conf import settings
from django.db import models, IntegrityError
from django.db.models.signals import post_save  # , pre_save , pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

from oneflow.base.utils import register_task_method
from oneflow.base.utils.http import clean_url
from oneflow.base.utils.dateutils import datetime

from ..common import (
    DjangoUser as User,

    ARTICLE_ORPHANED_BASE,
)

from base import BaseItem  # , baseitem_pre_save

from abstract import (
    UrlItem,
    ContentItem,
    baseitem_absolutize_url_task,
    baseitem_fetch_content_task,
)

from original_data import baseitem_postprocess_original_data_task

LOGGER = logging.getLogger(__name__)

MIGRATION_DATETIME = datetime(2014, 11, 1)


__all__ = [
    'Article',

    # Tasks will be added below.
]


# BIG FAT WARNING: order matters, BaseItem must come first,
# else `create_post_task()` is not found by register_task_method().
class Article(BaseItem, UrlItem, ContentItem):

    """ Some kind of news article, or web page. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Article')
        verbose_name_plural = _(u'Articles')

    publishers = models.ManyToManyField(
        User, null=True, blank=True, related_name='publications')

    date_published = models.DateTimeField(
        verbose_name=_(u'date published'),
        null=True, blank=True, db_index=True,
        help_text=_(u"When the article first appeared on the publisher's "
                    u"website."))

    # —————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        return _(u'{0} (#{1}) from {2}').format(
            self.name[:40] + (self.name[40:] and u'…'), self.id, self.url)

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def date_published_delta(self):

        with django_language():
            return _(u'{0} ago').format(naturaldelta(self.date_published))

    @property
    def is_good(self):
        """ Return True if all our base classes don't return False. """

        if not BaseItem.is_good.fget(self) \
            or not UrlItem.is_good.fget(self) \
                or not ContentItem.is_good.fget(self):
            return False

        return True

    # ————————————————————————————————————————————————————————————————— Methods

    @classmethod
    def create_article(cls, title, url, feeds, **kwargs):
        """ Returns ``True`` if article created, ``False`` if a pure duplicate
            (already exists in the same feed), ``None`` if exists but not in
            the same feed. If more than one feed given, only returns ``True``
            or ``False`` (mutualized state is not checked). """

        if url is None:
            reset_url = True
            # Even for a temporary action, we need something unique…
            url = ARTICLE_ORPHANED_BASE + uuid.uuid4().hex

        else:
            reset_url = False
            url = clean_url(url)

        new_article = cls(name=title, url=url)

        try:
            new_article.save()

        except IntegrityError:
            LOGGER.info(u'Duplicate article “%s” (url: %s) in feed(s) %s.',
                        title, url, u', '.join(unicode(f) for f in feeds))

            cur_article = cls.objects.get(url=url)

            created_retval = False

            if len(feeds) == 1 and feeds[0] not in cur_article.feeds.all():
                # This article is already there, but has not yet been
                # fetched for this feed. It's mutualized, and as such
                # it is considered at partly new. At least, it's not
                # as bad as being a true duplicate.
                created_retval = None

            cur_article.feeds.add(*feeds)

            return cur_article, created_retval

        tags = kwargs.pop('tags', [])

        if tags:
            new_article.tags.add(*tags)

        need_save = False

        if kwargs:
            need_save = True

            for key, value in kwargs.items():
                setattr(new_article, key, value)

        if reset_url:
            need_save = True
            new_article.url = \
                ARTICLE_ORPHANED_BASE + unicode(new_article.id)
            new_article.is_orphaned = True

            statsd.gauge('articles.counts.orphaned', 1, delta=True)

        if need_save:
            # Need to save because we will reload just after.
            new_article.save()

        if feeds:
            new_article.feeds.add(*feeds)

        LOGGER.info(u'Created %sarticle %s in feed(s) %s.', u'orphaned '
                    if reset_url else u'', new_article,
                    u', '.join(unicode(f) for f in feeds))

        return new_article, True

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            self.slug = slugify(self.name)
            self.save()

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.total', 1, delta=True)
                spipe.gauge('articles.counts.empty', 1, delta=True)

        post_absolutize_chain = tasks_chain(
            # HEADS UP: both subtasks are immutable, we just
            # want the group to run *after* the absolutization.

            # HEADS UP: this task name will be registered later
            # by the register_task_method call.
            baseitem_fetch_content_task.si(self.id),
            baseitem_postprocess_original_data_task.si(self.id),
        )

        # Randomize the absolutization a little, to avoid
        # http://dev.1flow.net/development/1flow-dev-alternate/group/1243/
        # as much as possible. This is not yet a full-featured solution,
        # but it's completed by the `fetch_limit` thing.
        #
        # Absolutization conditions everything else. If it doesn't succeed:
        #   - no bother trying to post-process author data for example,
        #     because we need the absolutized website domain to make
        #     authors unique and worthfull.
        #   - no bother fetching content: it uses the same mechanisms as
        #     absolutize_url(), and will probably fail the same way.
        #
        # Thus, we link the post_absolutize_chain as a callback. It will
        # be run only if absolutization succeeds. Thanks, celery :-)
        #
        # HEADS UP: this task name will be registered later
        # by the register_task_method call.
        baseitem_absolutize_url_task.apply_async((self.id, ),
                                                 link=post_absolutize_chain)

        #
        # TODO: create short_url
        #

        # TODO: remove_useless_blocks, eg:
        #       <p><a href="http://addthis.com/bookmark.php?v=250">
        #       <img src="http://cache.addthis.com/cachefly/static/btn/
        #       v2/lg-share-en.gif" alt="Bookmark and Share" /></a></p>
        #
        #       (in 51d6a1594adc895fd21c3475, see Notebook)
        #
        # TODO: link_replace (by our short_url_link for click statistics)
        # TODO: images_fetch
        #       eg. handle <img alt="2013-05-17_0009.jpg"
        #           data-lazyload-src="http://www.vcsphoto.com/blog/wp-content/uploads/2013/05/2013-05-17_0009.jpg" # NOQA
        #           src="http://www.vcsphoto.com/blog/wp-content/themes/prophoto4/images/blank.gif" # NOQA
        #           height="1198" sidth="900"/>
        #
        # TODO: authors_fetch
        # TODO: publishers_fetch
        # TODO: duplicates_find (content wise, not URL wise)
        #

        return


# ———————————————————————————————————————————————————————————————— Celery Tasks


register_task_method(Article, Article.post_create_task,
                     globals(), queue=u'high')

# register_task_method(Article, Article.find_image,
#                      globals(), queue=u'fetch', default_retry_delay=3600)
# register_task_method(Article, Article.replace_duplicate_everywhere,
#                      globals(), queue=u'low')

# ————————————————————————————————————————————————————————————————————— Signals


def article_post_save(instance, **kwargs):

    article = instance

    if kwargs.get('created', False):

        # Some articles are created "already orphaned" or duplicates.
        # In the archive database this is more immediate than looking
        # up the database name.
        if not (article.is_orphaned or article.duplicate_of):

            #
            # HEADS UP: MIGRATION. remove when finished.
            if article.date_created < MIGRATION_DATETIME:
                # SKIP everything, we already have the data from the migration.
                return

            # HEADS UP: this task name will be registered later
            # by the register_task_method() call.
            article_post_create_task.delay(article.id)  # NOQA


post_save.connect(article_post_save, sender=Article)
