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

from statsd import statsd
# from constance import config

from celery import chain as tasks_chain

from django.db import models, IntegrityError
from django.db.models.signals import post_save, pre_save, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

from oneflow.base.utils import register_task_method
from oneflow.base.utils.http import clean_url
from oneflow.base.utils.dateutils import now, datetime, benchmark

from ..common import (
    DjangoUser as User,
    CONTENT_TYPES,
    ARTICLE_ORPHANED_BASE,
)

from common import generate_orphaned_hash

from base import (
    BaseItemQuerySet,
    BaseItemManager,
    BaseItem,
)

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
    'create_article_from_url',

    # Tasks will be added below.
]


def create_article_from_url(url, feeds, origin):
    """ Create an article from a web url, in feeds, with an origin. """

    # TODO: find article publication date while fetching content…
    # TODO: set Title during fetch…

    try:
        new_article, created = Article.create_article(
            url=url.replace(' ', '%20'),
            title=_(u'Imported item from {0}').format(clean_url(url)),
            feeds=feeds, origin=origin)

    except:
        # NOTE: duplication handling is already
        # taken care of in Article.create_article().
        LOGGER.exception(u'Article creation from URL %s failed.', url)
        return None, False

    mutualized = created is None

    if created or mutualized:
        for feed in feeds:
            feed.recent_items_count += 1
            feed.all_items_count += 1

    for feed in feeds:
        if new_article.date_published:
            if new_article.date_published > feed.latest_item_date_published:
                feed.latest_item_date_published = new_article.date_published

        # Even if the article wasn't created, we need to create reads.
        # In the case of a mutualized article, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.
        for subscription in feed.subscriptions.all():
            subscription.create_read(new_article, verbose=created)

    # Don't forget the parenthesis else we return ``False`` everytime.
    return new_article, created or (None if mutualized else False)


# —————————————————————————————————————————————————————————— Manager / QuerySet


def BaseItemQuerySet_article_method(self):
    """ Patch BaseItemQuerySet to know how to return articles. """

    return self.instance_of(Article)


BaseItemQuerySet.article = BaseItemQuerySet_article_method


# ——————————————————————————————————————————————————————————————————————— Model

# BIG FAT WARNING: inheritance order matters. BaseItem must come first,
# else `create_post_task()` is not found by register_task_method().
class Article(BaseItem, UrlItem, ContentItem):

    """ Some kind of news article, or web page. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Article')
        verbose_name_plural = _(u'Articles')

    objects = BaseItemManager()

    publishers = models.ManyToManyField(
        User, null=True, blank=True, related_name='publications')

    # —————————————————————————————————————————————————————————————— Django

    def __unicode__(self):
        return _(u'{0} (#{1}) from {2}').format(
            self.name[:40] + (self.name[40:] and u'…'), self.id, self.url)

    # —————————————————————————————————————————————————————————————— Properties

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

        cur_article = None
        new_article = None

        if url is None:
            # We have to build a reliable orphaned URL, because orphaned
            # articles are often duplicates. RSS feeds serve us many times
            # the same article, without any URL, and we keep recording it
            # as new (but orphaned) content… Seen 20141111 on Chuck Norris
            # facts, where the content is in the title, and there is no URL.
            # We have 860k+ items, out of 1k real facts… Doomed.
            url = ARTICLE_ORPHANED_BASE + generate_orphaned_hash(title, feeds)

            try:
                cur_article = cls.objects.get(url=url)

            except cls.DoesNotExist:
                new_article = cls(name=title, url=url,
                                  is_orphaned=True,
                                  # Skip absolutization, it's useless.
                                  url_absolute=True)
                new_article.save()

                # HEADS UP: no statsd here, it's handled by post_save().

        else:
            url = clean_url(url)

            new_article = cls(name=title, url=url)

            try:
                new_article.save()

            except IntegrityError:
                cur_article = cls.objects.get(url=url)

        if cur_article:
            created_retval = False

            if len(feeds) == 1 and feeds[0] not in cur_article.feeds.all():
                # This article is already there, but has not yet been
                # fetched for this feed. It's mutualized, and as such
                # it is considered at partly new. At least, it's not
                # as bad as being a true duplicate.
                created_retval = None

                LOGGER.info(u'Mutualized article “%s” (url: %s) in feed(s) %s.',
                            title, url, u', '.join(unicode(f) for f in feeds))

            else:
                # No statsd, because we didn't create any record in database.
                LOGGER.info(u'Duplicate article “%s” (url: %s) in feed(s) %s.',
                            title, url, u', '.join(unicode(f) for f in feeds))

            try:
                cur_article.feeds.add(*feeds)

            except IntegrityError:
                LOGGER.exception(u'Could not add article %s to feeds %s',
                                 cur_article, feeds)

            return cur_article, created_retval

        need_save = False

        if kwargs:
            need_save = True

            for key, value in kwargs.items():
                setattr(new_article, key, value)

        if need_save:
            # Need to save because we will reload just after.
            new_article.save()

        LOGGER.info(u'Created %sarticle %s in feed(s) %s.', u'orphaned '
                    if new_article.is_orphaned else u'', new_article,
                    u', '.join(unicode(f) for f in feeds))

        # Tags & feeds are ManyToMany, they
        # need the article to be saved before.

        tags = kwargs.pop('tags', [])

        if tags:
            new_article.tags.add(*tags)

        if feeds:
            try:
                new_article.feeds.add(*feeds)
            except:
                LOGGER.exception(u'Could not add article %s to feeds %s',
                                 new_article, feeds)

        return new_article, True

    def post_create_task(self, apply_now=False):
        """ Method meant to be run from a celery task. """

        if apply_now:
            try:
                baseitem_absolutize_url_task.apply((self.id, ))
                baseitem_fetch_content_task.apply((self.id, ))
                baseitem_postprocess_original_data_task.apply((self.id, ))

            except:
                LOGGER.exception(u'Applying Article.post_create_task(%s) '
                                 u'failed.', self)
            return

        post_absolutize_chain = tasks_chain(
            # HEADS UP: both subtasks are immutable, we just
            # want the group to run *after* the absolutization.

            baseitem_fetch_content_task.si(self.id),
            baseitem_postprocess_original_data_task.si(self.id),
        )

        # OLD NOTES: randomize the absolutization a little, to avoid
        # http://dev.1flow.net/development/1flow-dev-alternate/group/1243/
        # as much as possible. This is not yet a full-featured solution,
        # but it's completed by the `fetch_limit` thing.
        #
        # Absolutization is the condition of everything else. If it
        # doesn't succeed:
        #   - no bother trying to post-process author data for example,
        #     because we need the absolutized website domain to make
        #     authors unique and worthful.
        #   - no bother fetching content: it uses the same mechanisms as
        #     absolutize_url(), and will probably fail the same way.
        #
        # Thus, we link the post_absolutize_chain as a callback. It will
        # be run only if absolutization succeeds. Thanks, celery :-)

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

    @classmethod
    def repair_missing_authors_migration_201411(cls):

        # from oneflow.core.tasks.migration import vacuum_analyze

        articles = Article.objects.filter(
            authors=None,
            date_created__gt=datetime(2014, 10, 31))

        count = articles.count()
        done = 0

        LOGGER.info(u'Starting repairing %s missing authors @%s', count, now())

        with benchmark(u'Fix missing authors on rel-DB fetched content…'):

            for article in articles:
                article.postprocess_original_data(force=True)

                # if done % 25000 == 0:
                #     vacuum_analyze()

                done += 1


# ———————————————————————————————————————————————————————————————— Celery Tasks


register_task_method(Article, Article.post_create_task,
                     globals(), queue=u'create')

# register_task_method(Article, Article.find_image,
#                      globals(), queue=u'fetch', default_retry_delay=3600)

# ————————————————————————————————————————————————————————————————————— Signals


def article_pre_save(instance, **kwargs):
    """ Make a slug if none. """

    article = instance

    if not article.slug:
        article.slug = slugify(article.name)


def article_post_save(instance, **kwargs):

    article = instance

    if kwargs.get('created', False):

        with statsd.pipeline() as spipe:
            spipe.gauge('articles.counts.total', 1, delta=True)
            spipe.gauge('articles.counts.empty', 1, delta=True)

            if article.is_orphaned:
                spipe.gauge('articles.counts.orphaned', 1, delta=True)

            if article.duplicate_of:
                spipe.gauge('articles.counts.duplicates', 1, delta=True)

            if article.url_error:
                spipe.gauge('articles.counts.url_error', 1, delta=True)

            if article.content_error:
                spipe.gauge('articles.counts.content_error', 1, delta=True)

        # Some articles are created "already orphaned" or duplicates.
        # In the archive database this is more immediate than looking
        # up the database name.
        if not (article.is_orphaned or article.duplicate_of):

            # MIGRATION: remove this "if".
            if article.date_created >= MIGRATION_DATETIME:

                # HEADS UP: this task name will be registered later
                # by the register_task_method() call.
                article_post_create_task.delay(article.id)  # NOQA


def article_pre_delete(instance, **kwargs):

    article = instance

    with statsd.pipeline() as spipe:
        spipe.gauge('articles.counts.total', -1, delta=True)

        if article.is_orphaned:
            spipe.gauge('articles.counts.orphaned', -1, delta=True)

        if article.duplicate_of:
            spipe.gauge('articles.counts.duplicates', -1, delta=True)

        if article.url_error:
            spipe.gauge('articles.counts.url_error', -1, delta=True)

        if article.content_error:
            spipe.gauge('articles.counts.content_error', -1, delta=True)

        if article.content_type == CONTENT_TYPES.HTML:
            spipe.gauge('articles.counts.html', -1, delta=True)

        elif article.content_type in (CONTENT_TYPES.MARKDOWN, ):
            spipe.gauge('articles.counts.markdown', -1, delta=True)

        elif article.content_type in (None, CONTENT_TYPES.NONE, ):
            spipe.gauge('articles.counts.empty', -1, delta=True)


pre_delete.connect(article_pre_delete, sender=Article)
pre_save.connect(article_pre_save, sender=Article)
post_save.connect(article_post_save, sender=Article)
