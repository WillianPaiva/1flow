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
import gc
import mistune
import requests
import strainer
import html2text
import newspaper
import breadability.readable

from bs4 import BeautifulSoup
from statsd import statsd
from constance import config
from markdown_deux import markdown as mk2_markdown

# from celery import chain as tasks_chain
from celery.exceptions import SoftTimeLimitExceeded

# from humanize.time import naturaldelta
# from humanize.i18n import django_language

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

from oneflow.base.utils import register_task_method
from oneflow.base.utils.http import clean_url
# from oneflow.base.utils.dateutils import now
from oneflow.base.utils import (detect_encoding_from_requests_response,
                                RedisExpiringLock,
                                StopProcessingException)

from ...common import (
    NotTextHtmlException,
    # DjangoUser as User,

    CONTENT_TYPES,
    CONTENT_TYPES_FINAL,
    CONTENT_PREPARSING_NEEDS_GHOST,
    ORIGINS,
    REQUEST_BASE_HEADERS,
)
from ...website import WebSite

from ..base import BaseItem

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


# ——————————————————————————————————————————————————————————————————— end ghost


class ContentItem(models.Model):

    """ An abstract item that has a content and knows how to process it. """

    class Meta:
        abstract = True
        app_label = 'core'
        verbose_name = _(u'Content item')
        verbose_name_plural = _(u'Content items')

    image_url = models.URLField(verbose_name=_(u'image URL'),
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

    # ————————————————————————————————————————————————————————————————— Methods

    def fetch_content_must_abort(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_DISABLED:
            LOGGER.info(u'Article fetching disabled in configuration.')
            return True

        if self.content_type in CONTENT_TYPES_FINAL and not force:
            LOGGER.info(u'Article %s has already been fetched.', self)
            return True

        if self.content_error:
            if force:
                statsd.gauge('articles.counts.content_errors', -1, delta=True)
                self.content_error = u''

                if commit:
                    self.save()

            else:
                LOGGER.warning(u'Article %s has a fetching error, aborting '
                               u'(%s).', self, self.content_error)
                return True

        if self.url_error:
            LOGGER.warning(u'Article %s has an url error. Absolutize it to '
                           u'clear: %s.', self, self.url_error)
            return True

        if self.is_orphaned and not force:
            LOGGER.warning(u'Article %s is orphaned, cannot fetch.', self)
            return True

        if self.duplicate_of and not force:
            LOGGER.warning(u'Article %s is a duplicate, will not fetch.', self)
            return True

        return False

    def fetch_content(self, force=False, verbose=False, commit=True):

        if self.fetch_content_must_abort(force=force, commit=commit):
            return

        #
        # TODO: implement switch based on content type.
        #

        try:
            # The first that matches will stop the chain.
            self.fetch_content_bookmark(force=force, commit=commit)

            self.fetch_content_text(force=force, commit=commit)

        except StopProcessingException as e:
            LOGGER.info(u'Stopping processing of article %s on behalf of '
                        u'an internal caller: %s.', self, unicode(e))
            return

        except SoftTimeLimitExceeded as e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'Extraction took too long for article %s.', self)
            return

        except NotTextHtmlException as e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'No text/html to extract in article %s.', self)
            return

        except requests.ConnectionError as e:
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.error(u'Connection failed while fetching article %s.', self)
            return

        except Exception as e:
            # TODO: except urllib2.error: retry with longer delay.
            statsd.gauge('articles.counts.content_errors', 1, delta=True)
            self.content_error = str(e)
            self.save()

            LOGGER.exception(u'Extraction failed for article %s.', self)
            return

        self.activate_reads(verbose=verbose)

        # No more needed now that Markdown
        # contents are generated asynchronously.
        # self.prefill_cache()

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
            LOGGER.info(u'Article %s image already found.', self)
            return True

        if self.content_type not in (CONTENT_TYPES.MARKDOWN, ):
            LOGGER.warning(u'Article %s is not in Markdown format, '
                           u'aborting image lookup.', self)
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
            LOGGER.exception(u'Image extraction failed for article %s.', self)

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
            return self.feed.has_option(CONTENT_FETCH_LIKELY_MULTIPAGE)

        except:
            LOGGER.warning(u'likely_multipage_content() not Implemented…')
            return False

    def get_next_page_link(self, from_content):
        """ Try to find a “next page” link in the partial content given as
            parameter. """

        # soup = BeautifulSoup(from_content)

        return None

    # ————————————————————————————————————————————————————————— Content related

    def extract_and_set_title(self, content=None, force=False, commit=True):
        """ Try to extract title from the HTML content, and set the article
            title from there. """

        if self.origin != ORIGINS.WEBIMPORT and not force:
            LOGGER.warning(u'Skipped title extraction on non-imported article '
                           u'#%s (use `force=True`).', self.id)
            return

        if self.title and not self.title.endswith(self.url):
            # In normal conditions (RSS/Atom feeds), the title has already
            # been set by the fetcher task, from the feed. No need to do the
            # work twice.
            #
            # NOTE: this will probably change with twitter and other social
            # related imports, thus we'll have to rework the conditions.
            LOGGER.error(u'NO WAY I will rework already-set title of '
                         u'article #%s (even with `force=True`).', self.id)
            return

        if content is None:
            if self.content_type == CONTENT_TYPES.HTML:
                content = self.content

            else:
                # Sadly, we have to reget/reparse the content.
                # Hopefully, this is only used in extreme cases,
                # and not the common one.
                try:
                    content, encoding = self.prepare_content_text(url=self.url)

                except:
                    LOGGER.exception(u'Could not extract title of article %s',
                                     self)

        old_title = self.title

        try:
            self.title = BeautifulSoup(content).find('title'
                                                     ).contents[0].strip()

        except:
            LOGGER.exception(u'Could not extract title of article %s', self)

        else:
            LOGGER.info(u'Changed title of article #%s from “%s” to “%s”.',
                        self.id, old_title, self.title)

            self.slug = slugify(self.title)

        if commit:
            self.save()

        return content

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

    def fetch_content_text_one_page(self, url=None):
        """ Internal function. Please do not call.
            Use :meth:`fetch_content_text` instead. """

        content, encoding = self.prepare_content_text(url=url)

        if not encoding:
            LOGGER.warning(u'Could not properly detect encoding for '
                           u'article %s, using utf-8 as fallback.', self)
            encoding = 'utf-8'

        if config.ARTICLE_FETCHING_DEBUG:
            try:
                raise NotImplementedError(
                    'Review encode/decode for multi-parsers.')

                LOGGER.info(u'————————— #%s HTML %s > %s —————————'
                            u'\n%s\n'
                            u'————————— end #%s HTML —————————',
                            self.id, content.__class__.__name__, encoding,
                            content.decode(encoding), self.id)
            except:
                LOGGER.exception(u'Could not log source HTML content of '
                                 u'article %s.', self)

        self.extract_and_set_title(content, commit=False)

        successfully_parsed = False

        for parser in ('lxml', 'html5lib', ):

            STRAINER_EXTRACTOR = strainer.Strainer(parser=parser,
                                                   add_score=True)

            try:
                content = STRAINER_EXTRACTOR.feed(content, encoding=encoding)
                successfully_parsed = True

            except:
                LOGGER.exception(u'Strainer extraction [parser=%s] '
                                 u'failed for article %s', parser, self)

            del STRAINER_EXTRACTOR
            gc.collect()

            if successfully_parsed:
                break

        if not successfully_parsed:
            try:
                breadability_article = breadability.readable.Article(
                    content, url=self.url)
                content = breadability_article.readable
                successfully_parsed = True

            except:
                LOGGER.exception(u'Breadability extraction failed for '
                                 u'article %s', self)

        if not successfully_parsed:
            newspaper_article = newspaper.Article(url=self.url)
            newspaper_article.download()
            # newspaper_article.parse()
            content = newspaper_article.html

        # TODO: remove noscript blocks ?
        #
        # TODO: remove ads (after noscript because they
        #       seem to be buried down in them)
        #       eg. <noscript><a href="http://ad.doubleclick.net/jump/clickz.us/ # NOQA
        #       media/media-buying;page=article;artid=2280150;topcat=media;
        #       cat=media-buying;static=;sect=site;tag=measurement;pos=txt1;
        #       tile=8;sz=2x1;ord=123456789?" target="_blank"><img alt=""
        #       src="http://ad.doubleclick.net/ad/clickz.us/media/media-buying; # NOQA
        #       page=article;artid=2280150;topcat=media;cat=media-buying;
        #       static=;sect=site;tag=measurement;pos=txt1;tile=8;sz=2x1;
        #       ord=123456789?"/></a></noscript>

        if config.ARTICLE_FETCHING_DEBUG:
            try:
                raise NotImplementedError(
                    'Review encode/decode for multi-parsers.')

                LOGGER.info(u'————————— #%s CLEANED %s > %s —————————'
                            u'\n%s\n'
                            u'————————— end #%s CLEANED —————————',
                            self.id, content.__class__.__name__, encoding,
                            content.decode(encoding), self.id)
            except:
                LOGGER.exception(u'Could not log cleaned HTML content of '
                                 u'article %s.', self)

        return content, encoding

    def fetch_content_text(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_TEXT_DISABLED:
            LOGGER.info(u'Article text fetching disabled in configuration.')
            return

        if self.content_type in (None, CONTENT_TYPES.NONE):

            LOGGER.info(u'Parsing text content for article %s…', self)

            if self.likely_multipage_content():
                # If everything goes well, 'content' should be an utf-8
                # encoded strings. See the non-paginated version for details.
                content    = u''
                next_link  = self.url
                pages      = 0

                while next_link is not None:
                    pages       += 1
                    current_page, encoding = \
                        self.fetch_content_text_one_page(next_link)
                    content     += str(current_page)
                    next_link    = self.get_next_page_link(current_page)

                    if next_link:
                        self.pages_urls.append(next_link)

                LOGGER.info(u'Fetched %s page(s) for article %s.', pages, self)

            else:
                # first: http://www.crummy.com/software/BeautifulSoup/bs4/doc/#non-pretty-printing # NOQA
                # then: InvalidStringData: strings in documents must be valid UTF-8 (MongoEngine says) # NOQA
                content, encoding = self.fetch_content_text_one_page()

                if type(content) == type(u''):
                    # A modern too already did the job.
                    self.content = content

                else:
                    # Strainer gives us a non-unicode boo-boo.
                    self.content = content.decode(eventual_encoding=encoding)

            self.content_type = CONTENT_TYPES.HTML

            if self.content_error:
                statsd.gauge('articles.counts.content_errors', -1, delta=True)
                self.content_error = u''

            if commit:
                self.save()

            with statsd.pipeline() as spipe:
                spipe.gauge('articles.counts.empty', -1, delta=True)
                spipe.gauge('articles.counts.html', 1, delta=True)

        #
        # TODO: parse HTML links to find other 1flow articles and convert
        # the URLs to the versions we have in database. Thus, clicking on
        # these links should immediately display the 1flow version, from
        # where the user will be able to get to the public website if he
        # wants. NOTE: this is just the easy part of this idea ;-)
        #

        #
        # TODO: HTML word count here, before markdown ?
        #

        self.convert_to_markdown(force=force, commit=commit)

        LOGGER.info(u'Done parsing content for article %s.', self)

    def fetch_content_bookmark(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_DISABLED:
            LOGGER.info(u'Bookmarks fetching disabled in configuration.')
            return

        if self.content_type == CONTENT_TYPES.NONE:

            slashes_parts = [p for p in self.url.split(u'/') if p != u'']

            parts_nr = len(slashes_parts)

            if parts_nr > 5:
                # For sure, this is not a bookmark.
                return

            if parts_nr == 2:
                # This is a simple website link. For sure, a bookmark.
                # eg. we got ['http', 'www.mysite.com']

                self.content_type = CONTENT_TYPES.BOOKMARK

            # elif parts_nr < 5:
                # TODO: find a way to ask the user to choose if he wanted
                # to bookmark the website or just fetch the content.

                domain_dotted = slashes_parts[1]
                domain_dashed = domain_dotted.replace(u'.', u'-')

                self.image_url = (u'http://images.screenshots.com/'
                                  u'{0}/{1}-small.jpg').format(
                    domain_dotted, domain_dashed)

                self.content = (u'http://images.screenshots.com/'
                                u'{0}/{1}-large.jpg').format(
                    domain_dotted, domain_dashed)

                content = self.extract_and_set_title(commit=False)

                #
                # Use the fetched content to get
                # the description of the page, if any.
                #
                if content is not None:
                    try:
                        soup = BeautifulSoup(content)
                        for meta in soup.find_all('meta'):
                            if meta.attrs.get('name', 'none').lower() \
                                    == 'description':
                                self.excerpt = meta.attrs['content']

                    except:
                        LOGGER.exception(u'Could not extract description '
                                         u'of imported bookmark %s', self)

                    else:
                        LOGGER.info(u'Successfully set description to “%s”',
                                    self.excerpt)

                if commit:
                    self.save()

            # TODO: fetch something like
            # http://www.siteencyclopedia.com/{parts[1]}/
            # and put it in the excerpt.

            # TODO: generate a snapshot of the website and store the image.

                raise StopProcessingException(u'Done setting up bookmark '
                                              u'content for article %s.', self)

    # ———————————————————————————————————————————————————————— NOT SURE TO KEEP

    def fetch_content_image(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_IMAGE_DISABLED:
            LOGGER.info(u'Article video fetching disabled in configuration.')
            return

    def fetch_content_video(self, force=False, commit=True):

        if config.ARTICLE_FETCHING_VIDEO_DISABLED:
            LOGGER.info(u'Article video fetching disabled in configuration.')
            return

    # —————————————————————————————————————————————————————————————— Conversion

    def convert_to_markdown(self, force=False, commit=True):

        if config.ARTICLE_MARKDOWN_DISABLED:
            LOGGER.info(u'Article markdown convert disabled in '
                        u'configuration.')
            return

        if self.content_type == CONTENT_TYPES.MARKDOWN:
            if not force:
                LOGGER.info(u'Article %s already converted to Markdown.', self)
                return

            else:
                statsd.gauge('articles.counts.markdown', -1, delta=True)

        elif self.content_type != CONTENT_TYPES.HTML:
            LOGGER.warning(u'Article %s cannot be converted to Markdown, '
                           u'it is not currently HTML.', self)
            return

        LOGGER.info(u'Converting article %s to markdown…', self)

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

            LOGGER.exception(u'Markdown convert failed for article %s.', self)
            return e

        self.content_type = CONTENT_TYPES.MARKDOWN

        if self.content_error:
            statsd.gauge('articles.counts.content_errors', -1, delta=True)
            self.content_error = u''

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
            LOGGER.warning(u'Article %s has no website??? Post-processing '
                           u'aborted.', self)
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

# HEADS UP: we need to register against BaseItem, because ContentItem is
#           abstract and cannot run .objects.get() in register_task_method().
register_task_method(BaseItem, ContentItem.fetch_content,
                     globals(), queue=u'fetch', default_retry_delay=3600)
