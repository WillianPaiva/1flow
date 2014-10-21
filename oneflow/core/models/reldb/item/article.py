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
import feedparser

import re
import gc
import ast
import uuid
import mistune
import requests
import strainer
import html2text

from bs4 import BeautifulSoup
from statsd import statsd
from random import randrange
from constance import config
from markdown_deux import markdown as mk2_markdown
from jsonfield import JSONField

# from xml.sax import SAXParseException

from celery import chain as tasks_chain
from celery.exceptions import SoftTimeLimitExceeded

from humanize.time import naturaldelta
from humanize.i18n import django_language

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify
from django.template.loader import render_to_string
from django.template.loader import add_to_builtins

from oneflow.base.utils import register_task_method
from oneflow.base.utils.http import clean_url
from oneflow.base.utils.dateutils import now
from oneflow.base.utils import (detect_encoding_from_requests_response,
                            RedisExpiringLock,
                            StopProcessingException)

from ..common import (
    NotTextHtmlException,
    DjangoUser as User,

    CONTENT_TYPES,
    CONTENT_TYPES_FINAL,
    CONTENT_PREPARSING_NEEDS_GHOST,
    CONTENT_FETCH_LIKELY_MULTIPAGE,
    ORIGINS,
    ARTICLE_ORPHANED_BASE,
    REQUEST_BASE_HEADERS,
)

from base import BaseItem

LOGGER                = logging.getLogger(__name__)
feedparser.USER_AGENT = settings.DEFAULT_USER_AGENT


__all__ = [
    'Article',
]


# ————————————————————————————————————————————————————————————————— start ghost


if config.FEED_FETCH_GHOST_ENABLED:
    try:
        import ghost
    except:
        ghost = None  # NOQA
    else:
        GHOST_BROWSER = ghost.Ghost()

else:
    ghost = None  # NOQA


# Until we patch Ghost to use more than one Xvfb at the same time,
# we are tied to ensure there is only one running at a time.
global_ghost_lock = RedisExpiringLock('__ghost.py__')


# ——————————————————————————————————————————————————————————————————— end ghost


class Article(BaseItem):

    """ Some kind of news article, or a web page. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Article')
        verbose_name_plural = _(u'Articles')

    url = models.URLField(unique=True, verbose_name=_(u'Public URL'))

    url_absolute = models.BooleanField(
        verbose_name=_(u'Absolute URL'),
        default=False, blank=True,
        help_text=_(u'The article URL has been successfully absolutized '
                    u'to its unique and final location.'))

    url_error = models.TextField(
        verbose_name=_(u'URL fetch error'),
        null=True, blank=True,
        help_text=_(u'Error when absolutizing the URL'))

    pages_urls = JSONField(
        verbose_name=_(u'Next pages URLs'),
        default=u'[]', blank=True,
        help_text=_(u'In case of a multi-pages article, other pages URLs '
                    u'are stored here.'))

    is_orphaned = models.BooleanField(
        verbose_name=_(u'Orphaned'),
        default=False, blank=True,
        help_text=_(u'This article has no public URL anymore, or is '
                    u'unfetchable for some reason.'))

    publishers = models.ManyToManyField(User, blank=True)

    date_published = models.DateTimeField(
        verbose_name=_(u'date published'),
        null=True, blank=True,
        help_text=_(u"When the article first appeared on the publisher's "
                    u"website."))

    content = models.TextField(
        verbose_name=_(u'Content'),
        null=True, blank=True,
        help_text=_(u'Article content'))

    content_type = models.IntegerField(
        verbose_name=_(u'Content type'),
        null=True, blank=True,
        help_text=_(u'Type of article content (HTML, Markdown…)'))

    content_error = models.TextField(
        verbose_name=_(u'Error'),
        null=True, blank=True,
        help_text=_(u'Error when fetching content.'))

    word_count = models.IntegerField(verbose_name=_(u'Word count'),
                                     null=True, blank=True)

    # ————————————————————————————————————————————————————————————————— Methods

    def postprocess_guess_origin_data(self, force=False, commit=True):

        need_save = False

        if self.original_data.feedparser_hydrated:
            self.origin_type = ORIGINS.FEEDPARSER
            need_save        = True

        elif self.original_data.google_reader_hydrated:
            self.origin_type = ORIGINS.GOOGLE_READER
            need_save        = True

        if need_save:
            if commit:
                self.save()

            # Now that we have an origin type, re-run the real post-processor.
            self.postprocess_original_data(force=force, commit=commit)

    def postprocess_feedparser_data(self, force=False, commit=True):
        """ XXX: should disappear when feedparser_data is useless. """

        if self.original_data.feedparser_processed and not force:
            LOGGER.info('feedparser data already post-processed.')
            return

        fpod = self.original_data.feedparser_hydrated

        if fpod:
            if self.tags == [] and 'tags' in fpod:
                tags = list(
                    Tag.get_tags_set((
                        t['term']
                        # Sometimes, t['term'] can be None.
                        # http://dev.1flow.net/webapps/1flow/group/4082/
                        for t in fpod['tags'] if t['term'] is not None),
                        origin=self))

                self.update_tags(tags, initial=True, need_reload=False)
                self.safe_reload()

            if self.authors == []:
                Author.get_authors_from_feedparser_article(fpod,
                                                           set_to_article=self)

            if self.language is None:
                language = fpod.get('summary_detail', {}).get('language', None)

                if language is None:
                    language = fpod.get('title_detail', {}).get(
                        'language', None)

                if language is not None:
                    try:
                        self.language = language.lower()
                        self.save()

                    except:
                        # This happens if the language code of the
                        # feedparser data does not correspond to a
                        # Django setting language we support.
                        LOGGER.exception(u'Cannot set language %s on '
                                         u'article %s.', language, self)

            if self.orphaned:
                # We have a chance to get at least *some* content. It will
                # probably be incomplete, but this is better than nothing.

                detail = fpod.get('summary_detail', {})

                if detail:
                    detail_type = detail.get('type', None)
                    detail_value = detail.get('value', '')

                    # We need some *real* data, though
                    if len(detail_value) > 20:

                        if detail_type == 'text/plain':
                            self.content = detail_value
                            self.content_type = CONTENT_TYPES.MARKDOWN
                            self.save()

                            statsd.gauge('articles.counts.markdown',
                                         1, delta=True)

                        elif detail_type == 'text/html':
                            self.content = detail_value
                            self.content_type = CONTENT_TYPES.HTML
                            self.save()

                            statsd.gauge('articles.counts.html',
                                         1, delta=True)

                            self.convert_to_markdown()

                        else:
                            LOGGER.warning(u'No usable content-type found '
                                           u'while trying to recover article '
                                           u'%s content: %s => "%s".', self,
                                           detail_type, detail_value)
                    else:
                        LOGGER.warning(u'Empty (or nearly) content-type '
                                       u'found while trying to recover '
                                       u'orphaned article %s '
                                       u'content: %s => "%s".', self,
                                       detail_type, detail_value)
                else:
                    LOGGER.warning(u'No summary detail found while trying '
                                   u'to recover orphaned article %s '
                                   u'content.', self)

            if self.comments_feed is None:

                comments_feed_url = fpod.get('wfw_commentrss', None)

                if comments_feed_url:
                    self.comments_feed = comments_feed_url
                    self.save()

            # We don't care anymore, it's already in another database.
            # self.offload_attribute('feedparser_original_data')

        self.original_data.update(set__feedparser_processed=True)

    def postprocess_google_reader_data(self, force=False, commit=True):
        LOGGER.warning(u'postprocess_google_reader_data() is not implemented '
                       u'yet but it was called for article %s!', self)
