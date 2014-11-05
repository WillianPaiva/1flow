# -*- coding: utf-8 -*-
u"""
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

from sparks.foundations.classes import SimpleObject

from sparks.django.utils import NamedTupleChoices

REQUEST_BASE_HEADERS  = {'User-agent': settings.DEFAULT_USER_AGENT}

# Lower the default, we know good websites just work well.
requests.adapters.DEFAULT_RETRIES = 1

CONTENT_TYPES = NamedTupleChoices(
    'CONTENT_TYPES',

    # Nothing at all could be fetched / parsed (but we tried).
    ('NONE', 0, _(u'No content')),

    # Content is still HTML (probably the MD conversion failed).
    ('HTML', 1, _(u'HTML')),

    # This one is obsolete, but we keep it in case
    # it's still present in http://1flow.io/ database.
    #
    # Since Hotfix 0.20.11.5, we process markdown differently,
    # And need to know about the "old" processing method to be
    # able to fix it afterwards in the production database.
    ('MD_V1', 2, _(u'Markdown v1 (1flow internal, obsolete)')),

    # The current conversion model.
    ('MARKDOWN', 3, _(u'Markdown')),

    # The next/future one (supports footnotes and cool stuff).
    ('MULTIMD', 4, _(u'MultiMarkdown')),

    # Other types, which will probably go into dedicated models.
    ('IMAGE', 100, _(u'Image')),
    ('VIDEO', 200, _(u'Video')),
    ('BOOKMARK', 900, _(u'Bookmark')),
)

CONTENT_TYPES_FINAL = (
    CONTENT_TYPES.MARKDOWN,
    CONTENT_TYPES.MD_V1,
    CONTENT_TYPES.MULTIMD,
    CONTENT_TYPES.IMAGE,
    CONTENT_TYPES.VIDEO,
    CONTENT_TYPES.BOOKMARK,
)

CONTENT_PREPARSING_NEEDS_GHOST = 1
CONTENT_FETCH_LIKELY_MULTIPAGE = 2

# MORE CONTENT_PREPARSING_NEEDS_* TO COME

ORIGINS = NamedTupleChoices(
    'ORIGINS',
    ('NONE', 0, _(u'None or Unknown')),
    ('GOOGLE_READER', 1, _(u'Google Reader')),
    ('FEEDPARSER', 2, _(u'RSS/Atom')),
    ('WRITING', 3, _(u'User writing')),
    ('TWITTER', 4, _(u'Twitter')),
    ('WEBIMPORT', 5, _(u'Web import')),
    ('EMAIL_FEED', 6, _(u'E-mail')),
    ('FACEBOOK', 7, _(u'Facebook')),
    ('GOOGLEPLUS', 8, _(u'Google Plus')),
    ('INTERNAL', 99, _(u'1flow internal origin'))
)

DUPLICATE_STATUS = NamedTupleChoices(
    'DUPLICATE_STATUS',

    # The register_duplicate() method has completed, but the
    # replace_duplicate() task has not yet started.
    ('NOT_REPLACED', 0, _(u'not yet replaced')),

    # The replace_duplicate() task is currently running.
    ('REPLACING', 1, _(u'Replacing')),

    # In this state, given what the instance type is, it
    # can be safely deleted (eg. tags), or kept (articles).
    ('FINISHED', 2, _(u'Finished (no occurence left)')),

    # In this state, the replace_duplicate() task
    # must be run again to complete its operation.
    ('FAILED', 3, _(u'One or more replacing failed')),
)

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
    'imported_items': (USER_FEEDS_SITE_URL + u'imports',
                       _(u'Imported items of {0}')),
    'sent_items': (USER_FEEDS_SITE_URL + u'sent',
                   _(u'Items sent by {0}')),
    'received_items': (USER_FEEDS_SITE_URL + u'received',
                       _(u'Received items of {0}')),
    'written_items': (USER_FEEDS_SITE_URL + u'written',
                      _(u'Items written by {0}')),
}


RATINGS = SimpleObject(from_dict={
    'STARRED': 5.0,
    'RETWEET': 10.0,
})

from exceptions import (  # NOQA
    FeedIsHtmlPageException,
    FeedFetchException,
    NotTextHtmlException,
)

# ——————————————————————————————————————————————————————————————————— Functions


def lowername(objekt):
    """ return the ``name`` attribute of :param:`object`, lowered(). """

    return attrgetter('name')(objekt).lower()
