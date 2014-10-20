# -*- coding: utf-8 -*-
"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

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
import requests

from operator import attrgetter

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

REQUEST_BASE_HEADERS  = {'User-agent': settings.DEFAULT_USER_AGENT}

# Lower the default, we know good websites just work well.
requests.adapters.DEFAULT_RETRIES = 1

# Don't use any lang-dependant values (eg. _(u'NO CONTENT'))
CONTENT_NOT_PARSED       = None
CONTENT_TYPE_NONE        = 0
CONTENT_TYPE_HTML        = 1
# Since Hotfix 0.20.11.5, we process markdown differently,
# And need to know about the "old" processing method to be
# able to fix it afterwards in the production database.
CONTENT_TYPE_MARKDOWN_V1 = 2
CONTENT_TYPE_MARKDOWN    = 3
CONTENT_TYPE_IMAGE       = 100
CONTENT_TYPE_VIDEO       = 200
CONTENT_TYPE_BOOKMARK    = 900
CONTENT_TYPES_FINAL      = (CONTENT_TYPE_MARKDOWN,
                            CONTENT_TYPE_MARKDOWN_V1,
                            CONTENT_TYPE_IMAGE,
                            CONTENT_TYPE_VIDEO,
                            CONTENT_TYPE_BOOKMARK,
                            )

CONTENT_PREPARSING_NEEDS_GHOST = 1
CONTENT_FETCH_LIKELY_MULTIPAGE = 2

# MORE CONTENT_PREPARSING_NEEDS_* TO COME

ORIGIN_TYPE_NONE          = 0
ORIGIN_TYPE_GOOGLE_READER = 1
ORIGIN_TYPE_FEEDPARSER    = 2
ORIGIN_TYPE_STANDALONE    = 3
ORIGIN_TYPE_TWITTER       = 4
ORIGIN_TYPE_WEBIMPORT     = 5
ORIGIN_TYPE_EMAIL_FEED    = 6

CACHE_ONE_HOUR  = 3600
CACHE_ONE_DAY   = CACHE_ONE_HOUR * 24
CACHE_ONE_WEEK  = CACHE_ONE_DAY * 7
CACHE_ONE_MONTH = CACHE_ONE_DAY * 30

ARTICLE_ORPHANED_BASE = u'http://{0}/orphaned/article/'.format(
                        settings.SITE_DOMAIN)
BAD_SITE_URL_BASE     = u'http://badsite.{0}/'.format(
                        settings.SITE_DOMAIN)
USER_FEEDS_SITE_URL   = u'http://{0}'.format(settings.SITE_DOMAIN
                                             ) + u'/user/{user.id}/'
SPECIAL_FEEDS_DATA = {
    'imported_items': (USER_FEEDS_SITE_URL + 'imports',
                       _(u'Imported items of {0}')),
    'sent_items': (USER_FEEDS_SITE_URL + 'sent',
                   _(u'Items sent by {0}')),
    'received_items': (USER_FEEDS_SITE_URL + 'received',
                       _(u'Received items of {0}')),
    'written_items': (USER_FEEDS_SITE_URL + 'written',
                      _(u'Items written by {0}')),
}


# —————————————————————————————————————————————————————————————————— Exceptions


class FeedIsHtmlPageException(Exception):

    """ Raised when the parsed feed gives us an HTML content.

    instead of an XML (RSS/Atom) one.
    """

    pass


class FeedFetchException(Exception):

    """ Raised when an RSS/Atom feed cannot be fetched, for any reason. """

    pass


class NotTextHtmlException(Exception):

    """ Raised when the content of an article is not text/html.

    To switch to other parsers, without re-requesting the actual content.
    """

    def __init__(self, message, response):
        """ OMG, pep257, please. """

        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)
        self.response = response


# ——————————————————————————————————————————————————————————————————— Functions


def lowername(objekt):
    """ return the ``name`` attribute of :param:`object`, lowered(). """

    return attrgetter('name')(objekt).lower()
