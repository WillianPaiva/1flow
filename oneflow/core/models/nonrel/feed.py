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
import requests
import feedparser

from statsd import statsd
from constance import config
from collections import OrderedDict

from xml.sax import SAXParseException

from mongoengine import Q, Document, NULLIFY, PULL
from mongoengine.fields import (IntField, StringField, URLField, BooleanField,
                                ListField, ReferenceField, DateTimeField)
from mongoengine.errors import ValidationError

# from cache_utils.decorators import cached

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.validators import URLValidator

from ....base.utils import (register_task_method,
                            RedisExpiringLock,
                            RedisSemaphore,
                            HttpResponseLogProcessor)

from ....base.fields import IntRedisDescriptor, DatetimeRedisDescriptor
from ....base.utils import ro_classproperty
from ....base.utils.http import clean_url
from ....base.utils.dateutils import (now, timedelta, today, datetime,
                                      is_naive, make_aware, utc)

from .common import (DocumentHelperMixin,
                     FeedIsHtmlPageException,
                     FeedFetchException,
                     CONTENT_TYPES,
                     ORIGINS,
                     USER_FEEDS_SITE_URL,
                     BAD_SITE_URL_BASE,
                     SPECIAL_FEEDS_DATA)
# CACHE_ONE_WEEK)
from .tag import Tag
from .article import Article
from .user import User
from .website import WebSite

# from ..reldb.mailfeed import MailFeed


LOGGER                = logging.getLogger(__name__)
feedparser.USER_AGENT = settings.DEFAULT_USER_AGENT

__all__ = [
    'Feed',

    'feed_all_articles_count_default',
    'feed_good_articles_count_default',
    'feed_bad_articles_count_default',
    'feed_recent_articles_count_default',
    'feed_subscriptions_count_default',
]


# ————————————— issue https://code.google.com/p/feedparser/issues/detail?id=404


import dateutil.parser
import dateutil.tz


def dateutilDateHandler(aDateString):
    default_datetime = now()

    try:
        return dateutil.parser.parse(aDateString).utctimetuple()

    except:
        pass

    try:
        return dateutil.parser.parse(aDateString, ignoretz=True).utctimetuple()

    except:
        pass

    try:
        return dateutil.parser.parse(aDateString,
                                     default=default_datetime).utctimetuple()

    except:
        LOGGER.exception(u'Could not parse date string “%s” with '
                         u'custom dateutil parser.', aDateString)
        # If dateutil fails and raises an exception, this produces
        # http://dev.1flow.net/1flow/1flow/group/30087/
        # and the whole chain crashes, whereas
        # https://pythonhosted.org/feedparser/date-parsing.html#registering-a-third-party-date-handler  # NOQA
        # states any exception is silently ignored.
        # Obviously it's not the case.
        return None


feedparser.registerDateHandler(dateutilDateHandler)


# ——————————————————————————————————————————————————————————————————— end issue


def feed_all_articles_count_default(feed, *args, **kwargs):

    return feed.articles.count()


def feed_good_articles_count_default(feed, *args, **kwargs):

    return feed.good_articles.count()


def feed_bad_articles_count_default(feed, *args, **kwargs):

    return feed.bad_articles.count()


def feed_recent_articles_count_default(feed, *args, **kwargs):

    return feed.recent_articles.count()


def feed_subscriptions_count_default(feed, *args, **kwargs):

    return feed.subscriptions.count()


class Feed(Document, DocumentHelperMixin):

    # BIG DB migration 20141028
    bigmig_migrated = BooleanField(default=False)
    bigmig_reassigned = BooleanField(default=False)
    # END BIG DB migration

    name           = StringField(verbose_name=_(u'name'))
    url            = URLField(unique=True, verbose_name=_(u'url'))
    is_internal    = BooleanField(default=False)
    created_by     = ReferenceField(u'User', reverse_delete_rule=NULLIFY)
    site_url       = URLField(verbose_name=_(u'web site'),
                              help_text=_(u'Website public URL, linked to the '
                                          u'globe icon in the source selector. '
                                          u'This is not the XML feed URL.'))
    slug           = StringField(verbose_name=_(u'slug'))
    tags           = ListField(ReferenceField('Tag', reverse_delete_rule=PULL),
                               default=list, verbose_name=_(u'tags'),
                               help_text=_(u'This tags are used only when '
                                           u'articles from this feed have no '
                                           u'tags already. They are assigned '
                                           u'to new subscriptions too.'))
    languages      = ListField(StringField(max_length=5,
                               choices=settings.LANGUAGES),
                               verbose_name=_(u'Languages'),
                               required=False,
                               help_text=_(u'Set this to more than one '
                                           u'language to help article '
                                           u'language detection if none '
                                           u'is set in articles.'))
    date_added     = DateTimeField(default=now, verbose_name=_(u'date added'))
    restricted     = BooleanField(default=False, verbose_name=_(u'restricted'),
                                  help_text=_(u'Is this feed available only to '
                                              u'paid subscribers on its '
                                              u'publisher\'s web site?'))
    closed         = BooleanField(default=False, verbose_name=_(u'closed'),
                                  help_text=_(u'Indicate that the feed is not '
                                              u'fetched anymore (see '
                                              u'“closed_reason” for why). '
                                              u'/!\\ WARNING: do not just '
                                              u'tick the checkbox; there is '
                                              u'a programmatic procedure to '
                                              u'close a feed properly.'))
    date_closed    = DateTimeField(verbose_name=_(u'date closed'))
    closed_reason  = StringField(verbose_name=_(u'closed reason'))

    fetch_interval = IntField(default=config.FEED_FETCH_DEFAULT_INTERVAL,
                              verbose_name=_(u'fetch interval'))
    last_fetch     = DateTimeField(verbose_name=_(u'last fetch'))

    # TODO: move this into WebSite to avoid too much parallel fetches
    # when using multiple feeds from the same origin website.
    fetch_limit_nr = IntField(default=config.FEED_FETCH_PARALLEL_LIMIT,
                              verbose_name=_(u'fetch limit'),
                              help_text=_(u'The maximum number of articles '
                                          u'that can be fetched from the feed '
                                          u'in parallel. If less than %s, '
                                          u'do not touch: the workers have '
                                          u'already tuned it from real-life '
                                          u'results.'))

    # Stored directly from feedparser data to avoid wasting BW.
    last_etag      = StringField(verbose_name=_(u'last etag'))
    last_modified  = StringField(verbose_name=_(u'modified'))

    mail_warned    = ListField(StringField())
    errors         = ListField(StringField())
    options        = ListField(IntField())
    duplicate_of   = ReferenceField(u'Feed', reverse_delete_rule=NULLIFY)
    notes          = StringField(verbose_name=_(u'Notes'),
                                 help_text=_(u'Internal notes for 1flow '
                                             u'staff related to this feed.'))

    good_for_use = BooleanField(verbose_name=_(u'Shown in selector'),
                                default=False,
                                help_text=_(u'Make this feed available to new '
                                            u'subscribers in the selector '
                                            u'wizard. Without this, the user '
                                            u'can still subscribe but he '
                                            u'must know it and manually enter '
                                            u'the feed address.'))
    thumbnail_url  = URLField(verbose_name=_(u'Thumbnail URL'),
                              required=False,
                              help_text=_(u'Full URL of the thumbnail '
                                          u'displayed in the feed selector. '
                                          u'Can be hosted outside of 1flow.'))
    description_fr = StringField(verbose_name=_(u'Description (FR)'),
                                 help_text=_(u'Public description of the feed '
                                             u'in French language. '
                                             u'As Markdown.'))
    description_en = StringField(verbose_name=_(u'Description (EN)'),
                                 help_text=_(u'Public description of the feed '
                                             u'in English language. '
                                             u'As Markdown.'))

    meta = {
        'indexes': [
            'name',
            'site_url',
        ]
    }

    # ••••••••••••••••••••••••••••••• properties, cached descriptors & updaters

    # TODO: create an abstract class that will allow to not specify
    #       the attr_name here, but make it automatically created.
    #       This is an underlying implementation detail and doesn't
    #       belong here.
    latest_article_date_published = DatetimeRedisDescriptor(
        # 5 years ealier should suffice to get old posts when starting import.
        attr_name='f.la_dp', default=now() - timedelta(days=1826))

    all_articles_count = IntRedisDescriptor(
        attr_name='f.aa_c', default=feed_all_articles_count_default,
        set_default=True, min_value=0)

    good_articles_count = IntRedisDescriptor(
        attr_name='f.ga_c', default=feed_good_articles_count_default,
        set_default=True, min_value=0)

    bad_articles_count = IntRedisDescriptor(
        attr_name='f.ba_c', default=feed_bad_articles_count_default,
        set_default=True, min_value=0)

    recent_articles_count = IntRedisDescriptor(
        attr_name='f.ra_c', default=feed_recent_articles_count_default,
        set_default=True, min_value=0)

    subscriptions_count = IntRedisDescriptor(
        attr_name='f.s_c', default=feed_subscriptions_count_default,
        set_default=True, min_value=0)

    @ro_classproperty
    def good_feeds(cls):
        """ Return feeds suitable for use in the “add subscription”
            part of the source selector, eg feeds marked as usable by
            the administrators, not closed. """

        return cls.objects.filter(
            # not internal, still open and validated by a human.
            (Q(is_internal__ne=True)
             & Q(closed__ne=True)
             & Q(good_for_use=True))

            # And not being duplicate of any other feed.
            & (Q(duplicate_of__exists=False) | Q(duplicate_of=None))
        )

    @property
    def latest_article(self):

        latest = self.get_articles(1)

        try:
            return latest[0]

        except:
            return None

    def update_latest_article_date_published(self):
        """ This seems simple, but this operations costs a lot in MongoDB. """

        try:
            # This query should still cost less than the pure and bare
            # `self.latest_article.date_published` which will first sort
            # all articles of the feed before getting the first of them.
            self.latest_article_date_published = self.recent_articles.order_by(
                '-date_published').first().date_published
        except:
            # Don't worry, the default value of
            # the descriptor should fill the gaps.
            pass

    @property
    def recent_articles(self):
        return self.good_articles.filter(
            date_published__gt=today()
            - timedelta(
                days=config.FEED_ADMIN_MEANINGFUL_DELTA))

    def update_recent_articles_count(self, force=False):
        """ This task is protected to run only once per day,
            even if is called more. """

        urac_lock = RedisExpiringLock(self, lock_name='urac', expire_time=86100)

        if urac_lock.acquire() or force:
            self.recent_articles_count = self.recent_articles.count()

        elif not force:
            LOGGER.warning(u'No more than one update_recent_articles_count '
                           u'per day (feed %s).', self)
        #
        # Don't bother release the lock, this will
        # ensure we are not called until tomorrow.
        #

    def update_all_articles_count(self):

        self.all_articles_count = feed_all_articles_count_default(self)

    def update_subscriptions_count(self):

        self.subscriptions_count = feed_subscriptions_count_default(self)

    # •••••••••••••••••••••••••••••••••••••••••••• end properties / descriptors

    # Doesn't seem to work, because Grappelli doesn't pick up Mongo classes.
    #
    # @staticmethod
    # def autocomplete_search_fields():
    #     return ('name__icontains', 'url__icontains', 'site_url__icontains', )

    def __unicode__(self):
        return _(u'{0} (#{1})').format(self.name, self.id)

    @property
    def refresh_lock(self):
        try:
            return self.__refresh_lock

        except AttributeError:
            self.__refresh_lock = RedisExpiringLock(self, lock_name='fetch')
            return self.__refresh_lock

    @property
    def fetch_limit(self):
        """ XXX: not used until correctly implemented.
            I removed the code calling this method on 20130910.
        """

        try:
            return self.__limit_semaphore

        except AttributeError:
            self.__limit_semaphore = RedisSemaphore(self, self.fetch_limit_nr)
            return self.__limit_semaphore

    def set_fetch_limit(self):
        """ XXX: not used until correctly implemented.
            I removed the code calling this method on 20130910.
        """

        new_limit = self.fetch_limit.set_limit()
        cur_limit = self.fetch_limit_nr

        if cur_limit != new_limit:
            self.fetch_limit_nr = new_limit
            self.save()

            LOGGER.info(u'Feed %s parallel fetch limit set to %s.',
                        self, new_limit)

    #
    # NOTE: this is hard-coded in the various feed creation methods.
    #
    # @classmethod
    # def signal_pre_save_handler(cls, sender, document, **kwargs):
    #     feed = document
    #     for protocol in (u'http://', u'https://'):
    #         if feed.url.startswith(protocol + settings.SITE_DOMAIN):
    #             feed.is_internal = True
    #             break

    @classmethod
    def prepare_feed_url(cls, feed_url):

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

    @classmethod
    def create_feeds_from_url(cls, feed_url, creator=None, recurse=True):
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

        feed_url = cls.prepare_feed_url(feed_url)

        try:
            feed = Feed.objects.get(url=feed_url)

        except Feed.DoesNotExist:
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
            cls.check_feedparser_error(parsed_feed)

        except FeedIsHtmlPageException:
            if recurse:
                new_feeds = []

                for sub_url in cls.parse_feeds_urls(parsed_feed):
                    try:
                        new_feeds += cls.create_feeds_from_url(
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

            return [(cls(name=fp_feed.get('title',
                         u'Feed from {0}'.format(feed_url)),
                         good_for_use=True,
                         # Try the RSS description, then the Atom subtitle.
                         description_en=fp_feed.get(
                             'description',
                             fp_feed.get('subtitle', u'')),
                         url=feed_url,
                         created_by=creator,
                         site_url=clean_url(fp_feed.get('link',
                                            feed_url))).save(), True)]

    @classmethod
    def parse_feeds_urls(cls, parsed_feed, skip_comments=True):
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

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):
        """ Do whatever useful on Feed.post_save(). """

        feed = document

        if created:
            if feed._db_name != settings.MONGODB_NAME_ARCHIVE:
                # Update the feed immediately after creation.

                # HEADS UP: this task name will be registered later
                # by the register_task_method() call.
                feed_refresh_task.delay(feed.id)  # NOQA

    def has_option(self, option):
        return option in self.options

    def reopen(self, commit=True):
        """ Reopen the feed, clearing errors, date closed, etc. """

        self.errors[:]     = []
        self.closed        = False
        self.date_closed   = now()
        self.closed_reason = u'Reopen on %s' % now().isoformat()
        self.save()

        LOGGER.info(u'Feed %s has just beed re-opened.', self)

    def close(self, reason=None, commit=True):
        """ Close the feed with or without a reason. """

        self.update(set__closed=True, set__date_closed=now(),
                    set__closed_reason=reason or u'NO REASON GIVEN')

        LOGGER.info(u'Feed %s closed with reason "%s"!',
                    self, self.closed_reason)

        self.safe_reload()

    @property
    def articles(self):
        """ A simple version of :meth:`get_articles`. """

        return Article.objects(feeds__contains=self)

    @property
    def good_articles(self):
        """ Subscriptions should always use :attr:`good_articles` to give
            to users only useful content for them, whereas :class:`Feed`
            will use :attr:`articles` or :attr:`all_articles` to reflect
            real numbers.
        """

        #
        # NOTE: sync the conditions with @Article.is_good
        #       and invert them in @Feed.bad_articles
        #

        return self.articles(orphaned__ne=True, url_absolute=True).filter(
            Q(duplicate_of__exists=False) | Q(duplicate_of=None))

    @property
    def bad_articles(self):

        #
        # NOTE: invert these conditions in @Feed.good_articles
        #

        return self.articles(Q(orphaned=True) | Q(url_absolute=False)
                             | Q(duplicate_of__ne=None))

    def get_articles(self, limit=None):
        """ A parameter-able version of the :attr:`articles` property. """

        if limit:
            return self.articles.order_by('-date_published').limit(limit)

        return self.articles.order_by('-date_published')

    def validate(self, *args, **kwargs):
        try:
            super(Feed, self).validate(*args, **kwargs)

        except ValidationError as e:

            # We pop() because any error will close the feed, whatever it is.
            site_url_error = e.errors.pop('site_url', None)

            if site_url_error is not None:
                # Bad site URL. Not exactly harmfull, but not cool.
                #
                # WAS: if not 'bad_site_url' in self.mail_warned:
                #           self.mail_warned.append('bad_site_url')

                self.site_url = BAD_SITE_URL_BASE + self.site_url

                # Do not close the feed for that…
                # self.close('Bad site url: %s' % str(site_url_error))

            # We pop() because any error will close the feed, whatever it is.
            url_error = e.errors.pop('url', None)

            if url_error is not None:
                if not self.closed:
                    self.close(str(url_error))

            thumbnail_url_error = e.errors.get('thumbnail_url', None)

            if thumbnail_url_error is not None:
                if self.thumbnail_url == u'':
                    # Just make this field not required. `required=False`
                    # in the Document definition is not sufficient.
                    e.errors.pop('thumbnail_url')

            if e.errors:
                raise ValidationError('ValidationError', errors=e.errors)

    def error(self, message, commit=True, last_fetch=False):
        """ Take note of an error. If the maximum number of errors is reached,
            close the feed and return ``True``; else just return ``False``.

            :param last_fetch: as a commodity, set this to ``True`` if you
                want this method to update the :attr:`last_fetch` attribute
                with the value of ``now()`` (UTC). Default: ``False``.

            :param commit: as in any other Django DB-related method, set
                this to ``False`` if you don't want this method to call
                ``self.save()``. Default: ``True``.
        """

        LOGGER.error(u'Error on feed %s: %s.', self, message)

        # Put the errors more recent first.
        self.errors.insert(0, u'%s @@%s' % (message, now().isoformat()))

        if last_fetch:
            self.last_fetch = now()

        retval = False

        if len(self.errors) >= config.FEED_FETCH_MAX_ERRORS:
            if not self.closed:
                self.close(u'Too many errors on the feed. Last was: %s'
                           % self.errors[0],

                           # prevent self.close() to reload()
                           # us before we save().
                           commit=False)

                LOGGER.critical(u'Too many errors on feed %s, closed.', self)

            # Keep only the most recent errors.
            self.errors = self.errors[:config.FEED_FETCH_MAX_ERRORS]

            retval = True

        if commit:
            self.save()

        return retval

    def create_article_from_url(self, url):

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
            self.recent_articles_count += 1
            self.all_articles_count += 1

        self.latest_article_date_published = now()

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

        tags = list(Tag.get_tags_set((
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
            self.recent_articles_count += 1
            self.all_articles_count += 1

        # Update the "latest date" kind-of-cache.
        if date_published is not None and \
                date_published > self.latest_article_date_published:
            self.latest_article_date_published = date_published

        # Even if the article wasn't created, we need to create reads.
        # In the case of a mutualized article, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.
        for subscription in self.subscriptions:
            subscription.create_read(new_article, verbose=created)

        # Don't forget the parenthesis else we return ``False`` everytime.
        return created or (None if mutualized else False)

    def create_article_from_mail(self, article):
        """ Take a feedparser item and a list of Feed subscribers and
            feed tags, and create the corresponding Article and Read(s). """

        return

    def build_refresh_kwargs(self, for_type=None):
        """ Return a kwargs suitable for internal feed refreshing methods. """

        if for_type is None:
            for_type = ORIGINS.FEEDPARSER

        kwargs = {}

        if for_type == ORIGINS.EMAIL_FEED:
            kwargs['since'] = self.last_fetch
            return kwargs

        # ——————————————————————————————————————————————— RSS specifics

        # Implement last-modified & etag headers to save BW.
        # Cf. http://pythonhosted.org/feedparser/http-etag.html
        if self.last_modified:
            kwargs['modified'] = self.last_modified

        else:
            kwargs['modified'] = self.latest_article_date_published

        if self.last_etag:
            kwargs['etag'] = self.last_etag

        # Circumvent https://code.google.com/p/feedparser/issues/detail?id=390
        http_logger        = HttpResponseLogProcessor()
        kwargs['referrer'] = self.site_url
        kwargs['handlers'] = [http_logger]

        return kwargs, http_logger

    def refresh_must_abort(self, force=False, commit=True):
        """ Returns ``True`` if one or more abort conditions is met.
            Checks the feed cache lock, the ``last_fetch`` date, etc.
        """

        if self.closed:
            LOGGER.info(u'Feed %s is closed. refresh aborted.', self)
            return True

        if self.is_internal:
            LOGGER.info(u'Feed %s is internal, no need to refresh.', self)
            return True

        if config.FEED_FETCH_DISABLED:
            # we do not raise .retry() because the global refresh
            # task will call us again anyway at next global check.
            LOGGER.info(u'Feed %s refresh disabled by configuration.', self)
            return True

        # ————————————————————————————————————————————————  Try to acquire lock

        if not self.refresh_lock.acquire():
            if force:
                LOGGER.warning(u'Forcing refresh for feed %s, despite of '
                               u'lock already acquired.', self)
                self.refresh_lock.release()
                self.refresh_lock.acquire()
            else:
                LOGGER.info(u'Refresh for %s already running, aborting.', self)
                return True

        if self.last_fetch is not None and self.last_fetch >= (
                now() - timedelta(seconds=self.fetch_interval)):
            if force:
                LOGGER.warning(u'Forcing refresh of recently fetched feed %s.',
                               self)
            else:
                LOGGER.info(u'Last refresh of feed %s too recent, aborting.',
                            self)
                return True

        return False

    @classmethod
    def check_feedparser_error(cls, parsed_feed, feed=None):

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

    @staticmethod
    def throttle_fetch_interval(interval, news, mutualized,
                                duplicates, etag, modified):
        """ Try to adapt dynamically the fetch interval, to fetch more feeds
            that produce a lot of new entries, and less the ones that do not.

            Feeds which correctly implement etags/last_modified should not
            be affected negatively.

            Feeds producing a lot of news should see their interval lower
            quickly. Feeds producing only duplicates will be fetched less.
            Feeds producing mutualized will still be fetched fast, because
            they are producing new content, even if it mutualized with other
            feeds.

            Feeds producing nothing and that do not implement etags/modified
            should suffer a lot and burn in hell like sheeps.

            This is a static method to allow better testing from outside the
            class.
        """

        if news:
            if mutualized:
                if duplicates:
                    multiplicator = 0.8

                else:
                    multiplicator = 0.7

            elif duplicates:
                multiplicator = 0.9

            else:
                # Only fresh news. My Gosh, this feed
                # produces a lot! Speed up fetches!!
                multiplicator = 0.6

            if mutualized > min(5, config.FEED_FETCH_RAISE_THRESHOLD):
                # The thing is prolific. Speed up even more.
                multiplicator *= 0.9

            if news > min(5, config.FEED_FETCH_RAISE_THRESHOLD):
                # The thing is prolific. Speed up even more.
                multiplicator *= 0.9

        elif mutualized:
            # Speed up, also. But as everything was already fetched
            # by komrades, no need to speed up too much. Keep cool.

            if duplicates:
                multiplicator = 0.9

            else:
                multiplicator = 0.8

        elif duplicates:
            # If there are duplicates, either the feed doesn't use
            # etag/last_mod [correctly], either its a master/subfeed
            # for which articles have already been fetched by a peer.

            if etag or modified:
                # There is something wrong with the website,
                # it should not have offered us anything when
                # using etag/last_modified.
                multiplicator = 1.25

            else:
                multiplicator = 1.125

        else:
            # No duplicates (feed probably uses etag/last_mod) but no
            # new articles, nor mutualized. Keep up the good work, don't
            # change anything.
            multiplicator = 1.0

        interval *= multiplicator

        if interval > min(604800, config.FEED_FETCH_MAX_INTERVAL):
            interval = config.FEED_FETCH_MAX_INTERVAL

        if interval < max(60, config.FEED_FETCH_MIN_INTERVAL):
            interval = config.FEED_FETCH_MIN_INTERVAL

        return interval

    def refresh_rss_feed(self, force=False):
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
            Feed.check_feedparser_error(parsed_feed, self)

        except Exception as e:
            self.close(reason=unicode(e))
            return

        new_articles  = 0
        duplicates    = 0
        mutualized    = 0

        if feed_status == 304:
            LOGGER.info(u'No new content in feed %s.', self)

        else:
            tags = Tag.get_tags_set(getattr(parsed_feed, 'tags', []),
                                    origin=self)

            if tags != set(self.tags):
                # We consider the publisher knows the nature of his content
                # better than us, and we trust him about the tags he sets
                # on the feed. Thus, we don't union() with the new tags,
                # but simply replace current by new ones.
                LOGGER.info(u'Updating tags of feed %s from %s to %s.',
                            self.tags, tags)
                self.tags = list(tags)

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

    def refresh(self, force=False):
        """ Look for new content in a 1flow feed. """

        # In tasks, doing this is often useful, if
        # the task waited a long time before running.
        self.safe_reload()

        # HEADS UP: refresh_must_abort() has already acquire()'d our lock.
        if self.refresh_must_abort(force=force):
            self.refresh_lock.release()
            return

        try:
            data = self.refresh_rss_feed(force=force)

        except:
            LOGGER.exception(u'Could not refresh feed %s', self)
            self.refresh_lock.release()
            return

        if data is None:
            # An error occured and the feed has already been closed.
            self.refresh_lock.release()
            return

        new_articles, duplicates, mutualized = data

        if new_articles == duplicates == mutualized == 0:

            with statsd.pipeline() as spipe:
                spipe.incr('mongo.feeds.refresh.fetch.global.unchanged')

        else:
            with statsd.pipeline() as spipe:
                spipe.incr('mongo.feeds.refresh.fetch.global.updated')

        if not force:
            # forcing the refresh is most often triggered by admins
            # and developers. It should not trigger the adaptative
            # throttling computations, because it generates a lot
            # of false-positive duplicates, and will.

            new_interval = Feed.throttle_fetch_interval(self.fetch_interval,
                                                        new_articles,
                                                        mutualized,
                                                        duplicates,
                                                        self.last_etag,
                                                        self.last_modified)

            if new_interval != self.fetch_interval:
                LOGGER.info(u'Fetch interval changed from %s to %s '
                            u'for feed %s (%s new article(s), %s '
                            u'duplicate(s)).', self.fetch_interval,
                            new_interval, self, new_articles, duplicates)

                self.fetch_interval = new_interval

        with statsd.pipeline() as spipe:
            spipe.incr('mongo.feeds.refresh.global.fetched', new_articles)
            spipe.incr('mongo.feeds.refresh.global.duplicates', duplicates)
            spipe.incr('mongo.feeds.refresh.global.mutualized', mutualized)

        # Everything went fine, be sure to reset the "error counter".
        self.errors[:] = []

        self.last_fetch = now()
        self.save()

        with statsd.pipeline() as spipe:
            spipe.incr('mongo.feeds.refresh.fetch.global.done')

        # As the last_fetch is now up-to-date, we can release the fetch lock.
        # If any other refresh job comes, it will check last_fetch and will
        # terminate if called too early.
        self.refresh_lock.release()


register_task_method(Feed, Feed.refresh,
                     globals(), queue=u'medium')
register_task_method(Feed, Feed.update_all_articles_count,
                     globals(), queue=u'low')
register_task_method(Feed, Feed.update_subscriptions_count,
                     globals(), queue=u'low')
register_task_method(Feed, Feed.update_recent_articles_count,
                     globals(), queue=u'low')
register_task_method(Feed, Feed.update_latest_article_date_published,
                     globals(), queue=u'low')


# ——————————————————————————————————————————————————————— external delete rules
#                                            Defined here to avoid import loops


Feed.register_delete_rule(Article, 'feeds', PULL)


# ———————————————————————————————————————— external non-subscription properties
#                                            Defined here to avoid import loops


def User_web_import_feed_property_get(self):

    return get_or_create_special_feed(self, *SPECIAL_FEEDS_DATA['web_import'])


def User_sent_items_feed_property_get(self):

    return get_or_create_special_feed(self, *SPECIAL_FEEDS_DATA['sent_items'])


def User_received_items_feed_property_get(self):

    return get_or_create_special_feed(self,
                                      *SPECIAL_FEEDS_DATA['received_items'])


# @cached(CACHE_ONE_WEEK)
def get_or_create_special_feed(user, url_template, default_name):

    try:
        return Feed.objects.get(url=url_template.format(user=user))

    except Feed.DoesNotExist:

        #
        # NOTE: using the username in the feed name will allow other
        # users to easily subscribe to each other's import feeds, and
        # distinguish them if they have many.
        #

        return Feed(url=url_template.format(user=user),
                    name=default_name.format(
                        user.username or (u'#%s' % user.id)),

                    # TODO: make this dynamic, given the
                    # free/premium level of users ?
                    restricted=True,

                    # By default, these feeds are internal,
                    # not part of the add-subsription form.
                    is_internal=True,

                    site_url=USER_FEEDS_SITE_URL.format(user=user)).save()

        # This will be done in the subscription property. DRY.
        # Subscription.subscribe_user_to_feed(user, feed)


User.web_import_feed     = property(User_web_import_feed_property_get)
User.sent_items_feed     = property(User_sent_items_feed_property_get)
User.received_items_feed = property(User_received_items_feed_property_get)


# ——————————————————————————————————————————————————————————————————————— Utils


def feed_export_content_classmethod(cls, since, folder=None):
    """ Pull articles & feeds since :param:`param` and return them in a dict.

        if a feed has no new article, it's not represented at all. The returned
        dict is suitable to be converted to JSON.
    """

    def origin_type(origin_type):

        if origin_type in (ORIGINS.FEEDPARSER,
                           ORIGINS.GOOGLE_READER):
            return u'rss'

        if origin_type == ORIGINS.TWITTER:
            return u'twitter'

        if origin_type == ORIGINS.EMAIL_FEED:
            return u'email'

        # implicit:
        # if origin_type == (ORIGINS.NONE,
        #                   ORIGINS.WEBIMPORT):
        return u'web'

    def content_type(content_type):

        if content_type == CONTENT_TYPES.MARKDOWN:
            return u'markdown'

        if content_type == CONTENT_TYPES.HTML:
            return u'html'

        if content_type == CONTENT_TYPES.IMAGE:
            return u'image'

        if content_type == CONTENT_TYPES.VIDEO:
            return u'video'

        if content_type == CONTENT_TYPES.BOOKMARK:
            return u'bookmark'

    if folder is None:
        active_feeds = Feed.objects.filter(closed=False,
                                           is_internal=False).no_cache()
        active_feeds_count = active_feeds.count()

    else:
        # Avoid import cycle…
        from subscription import Subscription

        subscriptions = Subscription.objects.filter(folders=folder).no_cache()
        active_feeds = [s.feed for s in subscriptions if not s.feed.closed]
        active_feeds_count = len(active_feeds)

    exported_websites = {}
    exported_feeds = []
    total_exported_articles_count = 0

    if active_feeds_count:
        LOGGER.info(u'Starting feeds/articles export procedure with %s '
                    u'active feeds…', active_feeds_count)
    else:
        LOGGER.warning(u'Not running export procedure, we have '
                       u'no active feed. Is this possible?')
        return

    for feed in active_feeds:
        new_articles = feed.good_articles.filter(date_published__gte=since)
        new_articles_count = new_articles.count()

        if not new_articles_count:
            continue

        exported_articles = []

        for article in new_articles:
            exported_articles.append(OrderedDict(
                id=unicode(article.id),
                title=article.title,
                pages_url=[article.url],
                image_url=article.image_url,
                excerpt=article.excerpt,
                content=article.content,
                media=origin_type(article.origin_type),
                content_type=content_type(article.content_type),
                date_published=article.date_published,

                authors=[(a.name or a.origin_name) for a in article.authors],
                date_updated=None,
                language=article.language,
                text_direction=article.text_direction,
                tags=[t.name for t in article.tags],
            ))

        exported_articles_count = len(exported_articles)
        total_exported_articles_count += exported_articles_count

        website = WebSite.get_from_url(feed.site_url)

        try:
            exported_website = exported_websites[website.url]

        except:
            exported_website = OrderedDict(
                id=unicode(website.id),
                name=website.name,
                slug=website.slug,
                url=website.url,
            )

            exported_websites[website.url] = exported_website

        exported_feeds.append(OrderedDict(
            id=unicode(feed.id),
            name=feed.name,
            url=feed.url,
            thumbnail_url=feed.thumbnail_url,
            tags=[t.name for t in feed.tags],
            articles=exported_articles,
            website=exported_website,
        ))

        LOGGER.info(u'%s articles exported in feed %s.',
                    exported_articles_count, feed)

    exported_feeds_count = len(exported_feeds)

    LOGGER.info(u'%s feeds and %s total articles exported.',
                exported_feeds_count, total_exported_articles_count)

    return exported_feeds

setattr(Feed, 'export_content', classmethod(feed_export_content_classmethod))
