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
import requests
import newspaper
import feedparser

from statsd import statsd
from constance import config

from xml.sax import SAXParseException

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save  # , pre_delete
from django.utils.translation import ugettext_lazy as _
from django.core.validators import URLValidator

from oneflow.base.utils import HttpResponseLogProcessor
from oneflow.base.utils.http import clean_url
from oneflow.base.utils.dateutils import (now, datetime, is_naive,
                                          make_aware, utc)

from ..common import (
    FeedIsHtmlPageException,
    FeedFetchException,
    # CONTENT_TYPES,
    ORIGINS,
    # USER_FEEDS_SITE_URL,
    # BAD_SITE_URL_BASE,
    # SPECIAL_FEEDS_DATA
)

from ..website import WebSite
from ..item import Article
from ..tag import SimpleTag

from common import throttle_fetch_interval, dateutilDateHandler
from base import BaseFeed, basefeed_refresh_task, basefeed_pre_save

LOGGER = logging.getLogger(__name__)

__all__ = [
    'RssAtomFeed',
    'create_feeds_from_url',
    'prepare_feed_url',
    'parse_feeds_urls',
]

# —————————————————————————————————————————————— External modules configuration


feedparser.registerDateHandler(dateutilDateHandler)
feedparser.USER_AGENT = settings.DEFAULT_USER_AGENT


def check_feedparser_error(parsed_feed, feed=None):
    """ Check for harmless or harmfull feedparser errors. """

    if parsed_feed.get('bozo', None) is None:
        return

    error = parsed_feed.get('bozo_exception', None)

    if error is None:
        return

    # Charset declaration problems are harmless (until they are not).
    if str(error).startswith(u'document declared as'):
        LOGGER.warning(u'While checking %s: %s',
                       feed or parsed_feed, error)
        return

    # Different error values were observed on:
    #   - http://ntoll.org/
    #       SAX: "mismatched tag"
    #       One .html attribute
    #
    #   - http://www.bbc.co.uk/
    #       SAX: "not well-formed (invalid token)"
    #       One .html attribute
    #
    #   - http://blog.1flow.io/ (Tumblr blog)
    #       SAX: 'junk after document element'
    #       *NO* .html attribute
    #
    # But we still have a quite-reliable common base to determine
    # if the page is pure HTML or not. We have to hope HTML pages
    # are > 2Kb nowadays, else small pages could still be detected
    # as feeds.
    if isinstance(error, SAXParseException) \
        and len(parsed_feed.get('entries', [])) == 0 \
        and parsed_feed.get('version', u'') == u'' \
        and ('html' in parsed_feed.feed
             or 'summary' not in parsed_feed.feed
             or len(parsed_feed.feed.summary) > 2048):

        raise FeedIsHtmlPageException(u'URL leads to an HTML page, '
                                      u'not a real feed.')


def prepare_feed_url(feed_url):
    """ Try to validate an URL as much as possible. """

    feed_url = clean_url(feed_url)

    URLValidator()(feed_url)

    requests_response = requests.get(feed_url)

    if not requests_response.ok or requests_response.status_code != 200:
        raise Exception(u'Requests response is not OK/200, aborting')

    # Switch to the last hop of eventually (multiple-)redirected URLs.
    feed_url = requests_response.url

    # Be sure we get the XML result from them,
    # else FeedBurner gives us a poor HTML page…
    if u'feedburner' in feed_url and not feed_url.endswith(u'?format=xml'):
        feed_url += u'?format=xml'

    return feed_url


def create_feeds_from_url(feed_url, creator=None, recurse=True):
    """ Return a list of one or more tuple(s) ``(feed, created)``,
        from a given URL.

        If the URL given is an RSS/Atom URL, the method will create a feed
        (if not already in the database), and will return it associated
        with the ``created`` boolean, given if it was created now, or not.
        For consistency, the tuple will be returned in a list, so that this
        method *always* returns a list of tuples.

        If the URL is a simple website one, it will be opened and parsed
        to discover eventual RSS/Atom feeds referenced in the page headers,
        and the method will return a list of tuples.

        .. todo:: parse the content body to find any RSS/Atom feeds inside.
            Will make it easy to parse http://www.bbc.co.uk/news/10628494

        :param creator: a :class:`User` that will be set as the feed(s)
            creator. This will allow to eventually give acheivements to
            users, or at the contrary to ban them if they pollute the DB.

        :param recurse: In case of a simple web URL, this method will be
            called recursively. Subsequent calls will be non-recursive
            by default. You can consider this argument to be "internal".
    """

    feed_url = prepare_feed_url(feed_url)

    try:
        feed = RssAtomFeed.objects.get(url=feed_url)

    except RssAtomFeed.DoesNotExist:
        # We will create it now.
        pass

    else:
        # Get the right one for the user subscription.
        if feed.duplicate_of:
            return [(feed.duplicate_of, False)]

        else:
            return [(feed, False)]

    http_logger = HttpResponseLogProcessor()
    parsed_feed = feedparser.parse(feed_url, handlers=[http_logger])
    feed_status = http_logger.log[-1]['status']

    # Stop on HTTP errors before stopping on feedparser errors,
    # because he is much more lenient in many conditions.
    if feed_status in (400, 401, 402, 403, 404, 500, 502, 503):
        raise FeedFetchException(u'Error {0} when fetching feed {1}'.format(
            feed_status, feed_url))

    try:
        check_feedparser_error(parsed_feed)

    except FeedIsHtmlPageException:
        if recurse:
            new_feeds = []
            urls_to_try = set(parse_feeds_urls(parsed_feed))

            try:
                urls_to_try.union(set(newspaper.build(feed_url).feed_urls()))

            except:
                LOGGER.exception(u'Newspaper did not help finding feeds '
                                 u'from “%s”', feed_url)

            for sub_url in urls_to_try:
                try:
                    new_feeds += create_feeds_from_url(
                        sub_url, creator=creator, recurse=False)

                except FeedIsHtmlPageException:
                    # We don't warn for every URL we find,
                    # most of them are CSS/JS/whatever ones.
                    pass

                except:
                    LOGGER.exception(u'Could not create a feed from '
                                     u'recursed url {0} (from {1})'.format(
                                         sub_url, feed_url))

            if new_feeds:
                return new_feeds

            raise

        else:
            raise

    except Exception as e:
        raise Exception(u'Unparsable feed {0}: {1}'.format(feed_url, e))

    else:
        # Wow. FeedParser creates a <anything>.feed
        fp_feed = parsed_feed.feed
        website = WebSite.get_from_url(clean_url(
                                       fp_feed.get('link', feed_url)))
        new_feed = RssAtomFeed(
            name=fp_feed.get('title', u'Feed from {0}'.format(feed_url)),
            is_good=True,
            # Try the RSS description, then the Atom subtitle.
            description_en=fp_feed.get(
                'description',
                fp_feed.get('subtitle', u'')),
            url=feed_url,
            created_by=creator,
            website=website)
        new_feed.save()

        return [(new_feed, True)]


def parse_feeds_urls(parsed_feed, skip_comments=True):
    """ Will yield any RSS/Atom links discovered into a badly parsed
        feed. Luckily for us, feedparser does a lot in pre-munching
        the data.
    """

    try:
        links = parsed_feed.feed.links

    except:
        LOGGER.info(u'No links to discover in {0}'.format(
                    parsed_feed.href))

    else:

        for link in links:
            if link.get('rel', None) == 'alternate' \
                and link.get('type', None) in (u'application/rss+xml',
                                               u'application/atom+xml',
                                               u'text/xml', ):

                lower_title = link.get('title', u'').lower()

                if (
                    u'comments feed' in lower_title
                    or
                    u'comments for' in lower_title
                    or
                    u'comments on' in lower_title
                    or

                    # NOTE: unicode() is needed to avoid “Coercing to
                    # Unicode: needs string or buffer, not __proxy__”,
                    # triggered by ugettext_lazy, used to catch the
                    # language of the calling user to maximize chances of
                    # avoiding comments feeds.

                    unicode(_(u'comments feed')) in lower_title
                    or
                    unicode(_(u'comments for')) in lower_title
                    or
                    unicode(_(u'comments on')) in lower_title
                ) and skip_comments:
                    continue

                yield link.get('href')


# ————————————————————————————————————————————————————————————————————— Classes


class RssAtomFeed(BaseFeed):

    """ An RSS & Atom feed object. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'RSS/Atom feed')
        verbose_name_plural = _(u'RSS/Atom feeds')

    url = models.URLField(unique=True, max_length=512,
                          verbose_name=_(u'url'))

    website = models.ForeignKey(
        WebSite,
        verbose_name=_(u'Web site'),
        null=True, blank=True,
        related_name='feeds',
    )

    # Stored directly from feedparser data to avoid wasting BW.
    last_etag = models.CharField(verbose_name=_(u'last etag'),
                                 max_length=256, null=True,
                                 blank=True)
    last_modified  = models.CharField(verbose_name=_(u'modified'),
                                      max_length=64, null=True,
                                      blank=True)

    # —————————————————————————————————————————————————————— Django & Grappelli

    @staticmethod
    def autocomplete_search_fields():
        """ grappelli auto-complete method. """

        return ('name__icontains', 'url__icontains', 'site__url__icontains', )

    def __unicode__(self):
        """ Hello, pep257. I love you so. """

        return _(u'RssAtomFeed {0} (#{1})').format(self.name, self.id)

    # —————————————————————————————————————————————————————————— Internal utils

    def throttling_method(self, new_articles, mutualized, duplicates):

        return throttle_fetch_interval(self.fetch_interval,
                                       new_articles,
                                       mutualized,
                                       duplicates,
                                       bool(self.last_etag
                                            or self.last_modified))

    # —————————————————————————————————————————————————————— High-level methods

    def refresh_must_abort_internal(self):
        """ Specific conditions where an RSS/Atom feed should not refresh. """

        if config.FEED_FETCH_RSSATOM_DISABLED:
            LOGGER.info(u'RSS/Atom feed %s refresh disabled by dynamic '
                        u'configuration.', self)
            return True

        return False

    def build_refresh_kwargs(self):
        """ Return a kwargs suitable for RSS/Atom feed refreshing method. """

        kwargs = {}

        # Implement last-modified & etag headers to save BW.
        # Cf. http://pythonhosted.org/feedparser/http-etag.html
        if self.last_modified:
            kwargs['modified'] = self.last_modified

        else:
            kwargs['modified'] = self.latest_item_date_published

        if self.last_etag:
            kwargs['etag'] = self.last_etag

        # Circumvent https://code.google.com/p/feedparser/issues/detail?id=390
        http_logger        = HttpResponseLogProcessor()
        kwargs['handlers'] = [http_logger]

        if self.website:
            kwargs['referrer'] = self.website.url

        return kwargs, http_logger

    def refresh_feed_internal(self, force=False):
        """ Refresh an RSS feed. """

        LOGGER.info(u'Refreshing RSS feed %s…', self)

        feedparser_kwargs, http_logger = self.build_refresh_kwargs()
        parsed_feed = feedparser.parse(self.url, **feedparser_kwargs)

        # In case of a redirection, just check the last hop HTTP status.
        try:
            feed_status = http_logger.log[-1]['status']

        except IndexError as e:
            # The website could not be reached? Network
            # unavailable? on my production server???

            self.error(u'Could not refresh RSS/Atom feed ({0})'.format(
                       parsed_feed.get('bozo_exception', u'IndexError')),
                       last_fetch=True)
            return

        # Stop on HTTP errors before stopping on feedparser errors,
        # because he is much more lenient in many conditions.
        if feed_status in (400, 401, 402, 403, 404, 500, 502, 503):
            self.error(u'HTTP %s on %s' % (http_logger.log[-1]['status'],
                       http_logger.log[-1]['url']), last_fetch=True)
            return

        try:
            check_feedparser_error(parsed_feed, self)

        except Exception as e:
            self.close(reason=unicode(e))
            return

        new_articles  = 0
        duplicates    = 0
        mutualized    = 0

        if feed_status == 304:
            LOGGER.info(u'No new content in feed %s.', self)

            return new_articles, duplicates, mutualized

        tags = SimpleTag.get_tags_set(getattr(parsed_feed, 'tags', []),
                                      origin=self)

        self_tags = self.tags.all()

        if tags != set(self_tags):
            # We consider the publisher knows the nature of his content
            # better than us, and we trust him about the tags he sets
            # on the feed. Thus, we don't union() with the new tags,
            # but simply replace current by new ones.
            LOGGER.info(u'Updating tags of feed %s from %s to %s.',
                        self_tags, tags)

            self.tags = SimpleTag.filter(id__in=tuple(t.id for t in tags))

        for article in parsed_feed.entries:
            created = self.create_article_from_feedparser(article, tags)

            if created:
                new_articles += 1

            elif created is False:
                duplicates += 1

            else:
                mutualized += 1

        # Store the date/etag for next cycle. Doing it after the full
        # refresh worked ensures that in case of any exception during
        # the loop, the retried refresh will restart on the same
        # entries without loosing anything.
        self.last_modified = getattr(parsed_feed, 'modified', None)
        self.last_etag     = getattr(parsed_feed, 'etag', None)

        return new_articles, duplicates, mutualized

    def create_article_from_url(self, url):
        """ PLEASE REVIEW. """

        # TODO: find article publication date while fetching content…
        # TODO: set Title during fetch…

        if settings.SITE_DOMAIN in url:
            # The following code should not fail, because the URL has
            # already been idiot-proof-checked in core.forms.selector
            #   .WebPagesImportForm.validate_url()
            read_id = url[-26:].split('/', 1)[1].replace('/', '')

            # Avoid an import cycle.
            from .read import Read

            # HEADS UP: we just patch the URL to benefit from all the
            # Article.create_article() mechanisms (eg. mutualization, etc).
            url = Read.objects.get(id=read_id).article.url

        try:
            new_article, created = Article.create_article(
                url=url.replace(' ', '%20'),
                title=_(u'Imported item from {0}').format(clean_url(url)),
                feeds=[self], origin_type=ORIGINS.WEBIMPORT)

        except:
            # NOTE: duplication handling is already
            # taken care of in Article.create_article().
            LOGGER.exception(u'Article creation from URL %s failed in '
                             u'feed %s.', url, self)
            return None, False

        mutualized = created is None

        if created or mutualized:
            self.recent_items_count += 1
            self.all_items_count += 1

        self.latest_item_date_published = now()

        # Even if the article wasn't created, we need to create reads.
        # In the case of a mutualized article, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.
        for subscription in self.subscriptions:
            subscription.create_read(new_article, verbose=created)

        # Don't forget the parenthesis else we return ``False`` everytime.
        return new_article, created or (None if mutualized else False)

    def create_article_from_feedparser(self, article, feed_tags):
        """ Take a feedparser item and a list of Feed subscribers and
            feed tags, and create the corresponding Article and Read(s). """

        feedparser_content = getattr(article, 'content', None)

        if isinstance(feedparser_content, list):
            feedparser_content = feedparser_content[0]
            content = feedparser_content.get('value', None)

        else:
            content = feedparser_content

        try:
            date_published = datetime(*article.published_parsed[:6])

        except:
            date_published = None

        else:
            # This is probably a false assumption, but have currently no
            # simple way to get the timezone of the feed. Anyway, we *need*
            # an offset aware for later comparisons. BTW, in most cases,
            # feedparser already did a good job before reaching here.
            if is_naive(date_published):
                date_published = make_aware(date_published, utc)

        tags = list(SimpleTag.get_tags_set((
                    t['term'] for t in article.get('tags', [])
                    # Sometimes, t['term'] can be None.
                    # http://dev.1flow.net/webapps/1flow/group/4082/
                    if t['term'] is not None), origin=self) | set(feed_tags))

        try:
            new_article, created = Article.create_article(
                # Sometimes feedparser gives us URLs with spaces in them.
                # Using the full `urlquote()` on an already url-quoted URL
                # could be very destructive, thus we patch only this case.
                #
                # If there is no `.link`, we get '' to be able to `replace()`,
                # but in fine `None` is a more regular "no value" mean. Sorry
                # for the weird '' or None that just does the job.
                url=getattr(article, 'link', '').replace(' ', '%20') or None,

                # We *NEED* a title, but as we have no article.lang yet,
                # it must be language independant as much as possible.
                title=getattr(article, 'title', u' '),

                excerpt=content, date_published=date_published,
                feeds=[self], tags=tags, origin_type=ORIGINS.FEEDPARSER)

        except:
            # NOTE: duplication handling is already
            # taken care of in Article.create_article().
            LOGGER.exception(u'Article creation failed in feed %s.', self)
            return False

        if created:
            try:
                new_article.add_original_data('feedparser', unicode(article))

            except:
                # Avoid crashing on anything related to the archive database,
                # else reads are not created and statistics are not updated.
                # Not having the archive data is not that important. Not
                # having the reads created forces us to check everything
                # afterwise, which is very expensive. Not having stats
                # updated is not cool for graph-loving users ;-)
                LOGGER.exception(u'Could not create article content '
                                 u'in archive database.')

        mutualized = created is None

        if created or mutualized:
            self.recent_items_count += 1
            self.all_items_count += 1

        # Update the "latest date" kind-of-cache.
        if date_published is not None and \
                date_published > self.latest_item_date_published:
            self.latest_item_date_published = date_published

        # Even if the article wasn't created, we need to create reads.
        # In the case of a mutualized article, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.
        for subscription in self.subscriptions.all():
            subscription.create_read(new_article, verbose=created)

        # Don't forget the parenthesis else we return ``False`` everytime.
        return created or (None if mutualized else False)


# ————————————————————————————————————————————————————————————————————— Signals


def rssatomfeed_pre_save(instance, **kwargs):
    """ Try to link the new feed to its website. """

    feed = instance

    if feed.pk:
        # The feed already exists, don't bother.
        return

    if feed.website:
        return

    website = WebSite.get_from_url(feed.url)

    feed.website = website


def rssatomfeed_post_save(instance, **kwargs):

    if not kwargs.get('created', False):
        return

    statsd.gauge('feeds.counts.total', 1, delta=True)
    statsd.gauge('feeds.counts.rssatom', 1, delta=True)

# Because http://stackoverflow.com/a/24624838/654755 doesn't work.
pre_save.connect(basefeed_pre_save, sender=RssAtomFeed)

pre_save.connect(rssatomfeed_pre_save, sender=RssAtomFeed)
post_save.connect(rssatomfeed_post_save, sender=RssAtomFeed)
