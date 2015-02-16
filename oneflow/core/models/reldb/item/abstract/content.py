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

import re
import mistune
import requests
import html2text

from statsd import statsd
from constance import config
from markdown_deux import markdown as mk2_markdown

# from celery import chain as tasks_chain
# from celery.exceptions import SoftTimeLimitExceeded

# from humanize.time import naturaldelta
# from humanize.i18n import django_language

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

# from oneflow.base.utils import register_task_method
from oneflow.base.utils.http import clean_url
# from oneflow.base.utils.dateutils import now
from oneflow.base.utils import (
    detect_encoding_from_requests_response,
    RedisExpiringLock,
)

from ...common import (
    NotTextHtmlException,
    # DjangoUser as User,

    CONTENT_TYPES,
    CONTENT_TYPES_FINAL,
    CONTENT_PREPARSING_NEEDS_GHOST,
    REQUEST_BASE_HEADERS,
)
from ...website import WebSite
from ..base import BaseItemQuerySet  # BaseItem,


LOGGER = logging.getLogger(__name__)


__all__ = [
    'ContentItem',

    # tasks will be added by register_task_method()
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


# ——————————————————————————————————————————————————————————— QuerySet patching


def BaseItemQuerySet_empty_method(self):
    """ Patch BaseItemQuerySet to know how to return empty content. """

    return self.filter(content_type__in=[None, CONTENT_TYPES.NONE])


def BaseItemQuerySet_parsed_method(self):
    """ Patch BaseItemQuerySet to know how to return parsed content. """

    return self.filter(content_type__in=CONTENT_TYPES_FINAL)


def BaseItemQuerySet_content_error_method(self):
    """ Return items that have a content errors.

    This means items that have either:

    - their :attr:`content_error` field set.
    - any :attr:`processing_error` related to `content` category.
    """

    return self.filter(
        ~models.Q(content_error=None)
        | models.Q(processing_errors__item__categories__slug=u'content')
    )

BaseItemQuerySet.empty = BaseItemQuerySet_empty_method
BaseItemQuerySet.parsed = BaseItemQuerySet_parsed_method
BaseItemQuerySet.content_error = BaseItemQuerySet_content_error_method


# ——————————————————————————————————————————————————————————————————————— Model


class ContentItem(models.Model):

    """ An abstract item that has a content and knows how to process it. """

    class Meta:
        abstract = True
        app_label = 'core'
        verbose_name = _(u'Content item')
        verbose_name_plural = _(u'Content items')

    image_url = models.URLField(verbose_name=_(u'image URL'),
                                max_length=384,
                                null=True, blank=True)

    excerpt = models.TextField(
        verbose_name=_(u'Excerpt'),
        null=True, blank=True,
        help_text=_(u'Small excerpt of content, if applicable.'))

    content = models.TextField(
        verbose_name=_(u'Content'),
        null=True, blank=True,
        help_text=_(u'Article content'))

    content_type = models.IntegerField(
        verbose_name=_(u'Content type'),
        null=True, blank=True, db_index=True,
        help_text=_(u'Type of article content (HTML, Markdown…)'))

    content_error = models.TextField(
        verbose_name=_(u'Error'),
        null=True, blank=True,
        help_text=_(u'Error when fetching content.'))

    word_count = models.IntegerField(verbose_name=_(u'Word count'),
                                     null=True, blank=True)

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def is_good(self):

        # Explanation: even a no-content article can be displayed,
        # at least in iframe mode. Thus, we do not consider no-content
        # to mean “bad article”. 20140405.
        #
        # if self.content_type not in CONTENT_TYPES_FINAL:
        #    return False

        return True

    @property
    def word_count_TRANSIENT(self):
        """ TRANSIENT: until we store the words count, which implies to
            be able to compute it correctly, we do all the work here. """

        if self.word_count:
            return self.word_count

        else:
            if self.content_type in CONTENT_TYPES_FINAL:

                # TODO: exclude video / audio...

                if len(self.content) > config.READ_ARTICLE_MIN_LENGTH:
                    return len(self.content.split())

        return None

    @property
    def processing_parameters(self):
        """ Return a content-enabled item processing parameters.

        Currently, it's ``{}``.
        """

        return {}

    @property
    def is_processed(self):
        """ Return True if our content type is final. """

        return self.content_type in CONTENT_TYPES_FINAL

    # ————————————————————————————————————————————————————————————————— Methods

    def reset(self, force=False, commit=True):
        """ See :meth:`Article.reset`() for explanations. """

        if not force:
            LOGGER.warning(u'Cannot reset content without `force` argument.')
            return

        self.image_url = None

        try:
            # Revert the excerpt to what it was at `post_create()` time.
            self.excerpt = self.history.last().excerpt

        except AttributeError:
            # Happens when ContentItem instance has no history (yet).
            pass

        self.content = None
        self.content_type = None
        self.content_error = None
        self.word_count = None

        if commit:
            # We are reseting, don't waste a version.
            self.save_without_historical_record()

    def processing_must_abort(self, force=False, commit=True):
        """ Return True if processing of current instance must be aborted.

        This can be for various reasons.

        .. versionadded:: 0.90.x. This is the new method, used by the 2015
            processing infrastructure.
        """

        if ContentItem.is_processed.fget(self) and not force:
            LOGGER.info(u'%s %s has already been processed.',
                        self._meta.verbose_name, self.id)
            return True

        # Slug “content” is related to the current “ContentItem” model.
        content_processing_errors = self.processing_errors.filter(
            processor__categories__slug=u'content')

        if content_processing_errors.exists():
            count = content_processing_errors.count()

            if force:
                content_processing_errors.delete()

                LOGGER.info(u'%s %s: cleared %s content errors and restarting '
                            u'processing.', self._meta.verbose_name, self.id,
                            count)

            else:
                LOGGER.warning(u'%s %s has %s content error(s), processing '
                               u'aborted (latest: %s).',
                               self._meta.verbose_name, self.id,
                               content_processing_errors.latest().exception)
                return True

        # OLD content_error, should vanish when converted to processing_error.
        if self.content_error:
            if force:
                self.content_error = None

                if commit:
                    self.save()

            else:
                LOGGER.warning(u'%s %s has a fetching error, aborting '
                               u' processing (%s).', self._meta.verbose_name,
                               self.id, self.content_error)
                return True

        return False

    def make_excerpt(self, commit=False):
        """ This method assumes a markdown content. Test it before calling.

            References:

            http://fr.wikipedia.org/wiki/Droit_de_courte_citation
        """

        if self.content:
            content_length = len(self.content)

            if content_length < config.READ_ARTICLE_MIN_LENGTH:
                return None

            min_threshold = config.EXCERPT_PARAGRAPH_MIN_LENGTH
            ten_percent   = content_length / 10
            paragraphs    = [p for p in self.content.split('\n') if p]
            skipped_text  = False

            for index, paragraph in enumerate(paragraphs):
                paragraph = paragraph.strip()

                if paragraph.startswith(u'[') or paragraph.startswith(u'!['):
                    continue

                if len(paragraph) < min_threshold:
                    skipped_text = True
                    continue

                retest_lenght = True

                # Strip out images, then links, if any.
                # Striping images before links is mandatory to
                # avoid RE clash on images contained in links.
                try:
                    paragraph = re.sub(ur'\![[]([^]]+)[]][(][^)]+[)]',
                                       # Don't miss the “r” on repl,
                                       # else \1 group doesn't work.
                                       ur'\1', paragraph)
                except IndexError:
                    # No image.
                    pass

                try:
                    paragraph = re.sub(ur'[[]([^]]+)[]][(][^)]+[)]',
                                       # Don't miss the “r” on repl,
                                       # else \1 group doesn't work.
                                       ur'\1', paragraph)
                except IndexError:
                    # No link found in this paragraph.
                    retest_lenght = False

                try:
                    while paragraph[0] == u'#':
                        paragraph = paragraph[1:]

                except IndexError:
                    # The paragraph is empty.
                    continue

                # Re-test the length now that we don't have any link anymore.
                if retest_lenght and len(paragraph) < min_threshold:
                    skipped_text = True
                    continue

                while len(paragraph) > ten_percent:
                    paragraph = u' '.join(paragraph.split(u' ')[:-1])

                try:

                    final_excerpt = mistune.markdown(paragraph).strip()

                except:
                    LOGGER.exception(u'Mistune markdown conversion failed, '
                                     u'trying the markdown2 parser.')

                    try:
                        final_excerpt = mk2_markdown(paragraph).strip()

                    except:
                        return None

                else:
                    if skipped_text:
                        if final_excerpt.startswith(u'<p>'):
                            final_excerpt = final_excerpt[3:]

                        # Beware the intended ending space
                        final_excerpt = (u'<p><span class="muted">[…]</span> '
                                         + final_excerpt)

                    if index < len(paragraphs):
                        if final_excerpt.endswith(u'</p>'):
                            final_excerpt = final_excerpt[:-4]

                        # Beware the intended starting space
                        final_excerpt += u' <span class="muted">[…]</span></p>'

                    if commit:
                        self.excerpt = final_excerpt
                        self.save()

                    return final_excerpt

        return None

    # ——————————————————————————————————————————————————————————————————— Image

    def find_image_must_abort(self, force=False, commit=True):

        if self.image_url and not force:
            LOGGER.info(u'%s #%s image already found.',
                        self._meta.verbose_name, self.id)
            return True

        if self.content_type not in (CONTENT_TYPES.MARKDOWN, ):
            LOGGER.warning(u'%s #%s is not in Markdown format, '
                           u'aborting image lookup.',
                           self._meta.verbose_name, self.id)
            return True

    def find_image(self, force=False, commit=True):

        # __          __       _____   _   _  _____  _   _   _____
        # \ \        / //\    |  __ \ | \ | ||_   _|| \ | | / ____|
        #  \ \  /\  / //  \   | |__) ||  \| |  | |  |  \| || |  __
        #   \ \/  \/ // /\ \  |  _  / | . ` |  | |  | . ` || | |_ |
        #    \  /\  // ____ \ | | \ \ | |\  | _| |_ | |\  || |__| |
        #     \/  \//_/    \_\|_|  \_\|_| \_||_____||_| \_| \_____|
        #
        # Please modify core.views.article_image() when
        # the current method gets more love inside.

        if self.find_image_must_abort(force=force, commit=commit):
            return

        try:
            for match in re.finditer(ur'![[][^]]+[]][(]([^)]+)[)]',
                                     self.content):
                if match:
                    self.image_url = match.group(1)

                    if commit:
                        self.save()

                    return self.image_url

            if not self.image_url:

                a_feed = self.a_feed

                if a_feed and a_feed.thumbnail_url:
                    self.image_url = a_feed.thumbnail_url

                    if commit:
                        self.save()

                    return self.image_url

        except Exception:
            LOGGER.exception(u'Image extraction failed for %s #%s.',
                             self._meta.verbose_name, self.id)

        return None

    # ————————————————————————————————————————————————————————— Ghost subsystem

    def needs_ghost_preparser(self):

        try:
            # TODO: this should be coming from the website, not the feed.
            return config.FEED_FETCH_GHOST_ENABLED and \
                self.feed.has_option(CONTENT_PREPARSING_NEEDS_GHOST)

        except AttributeError:
            # self.feed can be None…
            return False

    # ——————————————————————————————————————————————— TO_MERGE_WITH ABSTRACT/URL

    def likely_multipage_content(self):

        try:
            # TODO: this should be coming from the website, not the feed.
            return self.feed.has_option(CONTENT_FETCH_LIKELY_MULTIPAGE)  # NOQA

        except:
            LOGGER.warning(u'likely_multipage_content() not Implemented…')
            return False

    def get_next_page_link(self, from_content):
        """ Try to find a “next page” link in the partial content given as
            parameter. """

        # soup = BeautifulSoup(from_content)

        return None

    # ————————————————————————————————————————————————————————— Content related

    def prepare_content_text(self, url=None):
        """ :param:`url` should be sinfon the case of multipage content. """

        if url is None:
            fetch_url = self.url

        else:
            fetch_url = url

        if self.needs_ghost_preparser():

            if ghost is None:
                LOGGER.warning(u'Ghost module is not available, content of '
                               u'article %s will be incomplete.', self)
                return requests.get(fetch_url,
                                    headers=REQUEST_BASE_HEADERS).content

                # The lock will raise an exception if it is already acquired.
                with global_ghost_lock:
                    GHOST_BROWSER.open(fetch_url)
                    page, resources = GHOST_BROWSER.wait_for_page_loaded()

                    #
                    # TODO: detect encoding!!
                    #
                    return page

        response = requests.get(fetch_url, headers=REQUEST_BASE_HEADERS)

        content_type = response.headers.get('content-type', u'unspecified')

        if content_type.startswith(u'text/html'):
            encoding = detect_encoding_from_requests_response(response)

            return response.content, encoding

        raise NotTextHtmlException(u"Content is not text/html "
                                   u"but %s." % content_type,
                                   response=response)

    # —————————————————————————————————————————————————————————————— Conversion

    def convert_to_markdown(self, force=False, commit=True):

        if config.ARTICLE_MARKDOWN_DISABLED:
            LOGGER.info(u'Article markdown convert disabled in '
                        u'configuration.')
            return

        if self.content_type == CONTENT_TYPES.MARKDOWN:
            if not force:
                LOGGER.info(u'%s #%s already converted to Markdown.',
                            self._meta.verbose_name, self.id)
                return

            else:
                statsd.gauge('articles.counts.markdown', -1, delta=True)

        elif self.content_type != CONTENT_TYPES.HTML:
            LOGGER.warning(u'%s #%s cannot be converted to Markdown, '
                           u'it is not currently HTML.',
                           self._meta.verbose_name, self.id)
            return

        LOGGER.info(u'Converting %s #%s to markdown…',
                    self._meta.verbose_name, self.id)

        md_converter = html2text.HTML2Text()

        # Set sane defaults. body_width > 0 breaks
        # some links by inserting \n inside them.
        #
        # MD_V1 had [False, False, 78] (=default parameters)
        md_converter.unicode_snob = True
        md_converter.escape_snob  = True
        md_converter.body_width   = 0

        try:
            # NOTE: everything should stay in Unicode during this call.
            self.content = md_converter.handle(self.content)

        except Exception as e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)

            self.content_error = str(e)
            self.save()

            LOGGER.exception(u'Markdown convert failed for item #%s.', self.id)
            return e

        self.content_type = CONTENT_TYPES.MARKDOWN

        if self.content_error:
            statsd.gauge('articles.counts.content_errors', -1, delta=True)
            self.content_error = None

        #
        # TODO: word count here
        #
        self.postprocess_markdown_links(commit=False, force=force)

        if commit:
            self.save()

        with statsd.pipeline() as spipe:
            spipe.gauge('articles.counts.html', -1, delta=True)
            spipe.gauge('articles.counts.markdown', 1, delta=True)

        if config.ARTICLE_FETCHING_DEBUG:
            LOGGER.info(u'————————— #%s Markdown %s —————————'
                        u'\n%s\n'
                        u'————————— end #%s Markdown —————————',
                        self.id, self.content.__class__.__name__,
                        self.content, self.id)

    def postprocess_markdown_links(self, force=False, commit=True, test=False):
        """ Clean and re-wrap article links as much as possible.

        - be sure we have no external links without the website part missing,
          else 1flow article internal links all point to 1flow, which makes
          them unusable.
        - more processing to come (eg. convert external URLs that we know to
          internal ones; use internal short_urls…)
        - BTW, if the current article is an "old" markdown V1 one, try to
          repair its links by removing the `\n` inside them.
        """

        if self.content_type == CONTENT_TYPES.MARKDOWN:
            replace_newlines = False

        elif self.content_type == CONTENT_TYPES.MD_V1:
            replace_newlines = True

        else:
            LOGGER.debug(u'Skipped non-Markdown article %s.', self)
            return

        website = WebSite.get_from_url(self.url)

        if website is None:
            LOGGER.warning(u'%s #%s has no website??? Post-processing '
                           u'aborted.', self._meta.verbose_name, self.id)
            return

        website_url = website.url

        def insert_website(link):
            if link.startswith(u'](/') or link.startswith(u'](.'):
                return u'](' + website_url + link[2:]

            else:
                return link

        # Use a copy during the operation to ensure we can start
        # again from scratch in a future call if anything goes wrong.
        content = self.content

        if replace_newlines:
            for repl_src in re.findall(ur'[[][^]]+[]][(]', content):

                # In link text, we replace by a space.
                repl_dst = repl_src.replace(u'\n', u' ')
                content  = content.replace(repl_src, repl_dst)

        for repl_src in re.findall(ur'[]][(][^)]+[)]', content):

            if replace_newlines:
                # In link URLs, we just cut out newlines.
                repl_dst = repl_src.replace(u'\n', u'')
            else:
                repl_dst = repl_src

            repl_dst = clean_url(insert_website(repl_dst))
            content  = content.replace(repl_src, repl_dst)

        if test:
            return content

        else:
            # Everything went OK. Put back the content where it belongs.
            self.content = content

            if replace_newlines:
                self.content_type = CONTENT_TYPES.MARKDOWN

            # Disabled until more love is put inside.
            # self.find_image(commit=False, force=force)

            if commit:
                self.save()

# ———————————————————————————————————————————————————————————————— Celery Tasks
