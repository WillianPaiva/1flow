# -*- coding: utf-8 -*-
u"""
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

from constance import config

# from django.conf import settings
# from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext_lazy as _

from sparks.django.utils import NamedTupleChoices


LOGGER = logging.getLogger(__name__)

# ——————————————————————————————————————————————————————————————————— Constants

RULES_OPERATIONS = NamedTupleChoices(
    'RULES_OPERATIONS',
    ('ANY', 1, _(u'Any rule matches')),
    ('ALL', 2, _(u'All rules must match')),
)

_COMMON_MATCH_TYPES = (
    ('EQUALS',     6, _(u'strictly equals')),
    ('NEQUALS',    7, _(u'is not equal to')),
)

_TEXT_MATCH_TYPES = (
    ('CONTAINS',   1, _(u'contains')),
    ('NCONTAINS',  2, _(u'does not contain')),
    ('STARTS',     3, _(u'starts with')),
    ('NSTARTS',    4, _(u'does not start with')),
    ('ENDS',       4, _(u'ends with')),
    ('NENDS',      5, _(u'does not end with')),
    ('RE_MATCH',   8, _(u'matches regular expression')),
    ('NRE_MATCH',  9, _(u'does not match reg. expr.')),
)

_NUMERIC_MATCH_TYPES = (
    ('LOWER',     20, _(u'is lower than')),
    ('LOWEREQ',   21, _(u'is lower or equal than')),
    ('GREATER',   22, _(u'is greater than')),
    ('GREATEREQ', 23, _(u'is greater or equal than')),
)

_SPECIAL_MATCH_TYPES = (
    ('EXISTS',     30, _(u'exists / is present')),
    ('NEXISTS',    31, _(u'does not exist / is not present')),
)

# —————————————————————————————————————————————————————————————————————— E-mail

# A simple copy, for the eventuality we could need a separate tuple.
MAIL_RULES_OPERATIONS = RULES_OPERATIONS
MAIL_MATCH_TYPES = NamedTupleChoices(*(
    ('MAIL_MATCH_TYPES', )
    + _TEXT_MATCH_TYPES
    + _COMMON_MATCH_TYPES
))

MAIL_MATCH_ACTIONS = NamedTupleChoices(
    'MAIL_MATCH_ACTIONS',

    ('STORE', 1, _(u'store email in the feed')),
    ('SCRAPE', 2, _(u'scrape email, extract links and fetch articles')),
    ('STORE_SCRAPE', 3,
     _(u'do both, eg. store email and extract links / fetch articles')),
)

MAIL_FINISH_ACTIONS = NamedTupleChoices(
    'MAIL_FINISH_ACTIONS',

    ('NOTHING', 1, _(u'leave e-mail untouched')),
    ('MARK_READ', 2, _(u'mark e-mail read')),
    ('DELETE', 3, _(u'delete e-mail')),
)

MAIL_HEADER_FIELDS = NamedTupleChoices(
    'MAIL_HEADER_FIELDS',

    ('SUBJECT', 1,  _(u'Subject')),
    ('FROM',    2, _(u'Sender')),
    ('TO',      3, _(u'Recipient (To:, Cc: or Bcc:)')),
    ('COMMON',  4, _(u'Subject or addresses')),

    # Not ready for that.
    # ('body',   5, _(u'Message body')),

    ('LIST',    6, _(u'Mailing-list')),
    ('OTHER',   7, _(u'Other header (please specify)')),
)

MAIL_HEADER_FIELD_DEFAULT = MAIL_HEADER_FIELDS.COMMON
MAIL_MATCH_TYPE_DEFAULT = MAIL_MATCH_TYPES.CONTAINS
MAIL_MATCH_ACTION_DEFAULT = MAIL_MATCH_ACTIONS.SCRAPE
MAIL_FINISH_ACTION_DEFAULT = MAIL_FINISH_ACTIONS.MARK_READ
MAIL_RULES_OPERATION_DEFAULT = RULES_OPERATIONS.ANY
MAIL_GROUP_OPERATION_DEFAULT = RULES_OPERATIONS.ANY

# ————————————————————————————————————————————————————————————— Twitter

# A simple copy, for the eventuality we could need a separate tuple.
TWITTER_RULES_OPERATIONS = RULES_OPERATIONS
TWITTER_MATCH_TYPES = NamedTupleChoices(*(
    ('TWITTER_MATCH_TYPES', )
    + _TEXT_MATCH_TYPES
    + _COMMON_MATCH_TYPES
    + _NUMERIC_MATCH_TYPES
    + _SPECIAL_MATCH_TYPES
))

TWITTER_MATCH_ACTIONS = NamedTupleChoices(
    'TWITTER_MATCH_ACTIONS',

    ('STORE_TWEET', 1, _(u'Store the tweet as is')),

    ('CRAWL_LINKS', 2,
     _(u'Crawl links in the tweet and fetch them as articles')),
    ('STORE_LINKS', 3, _(u'Crawl tweet links, store them and the tweet too')),

    ('CRAWL_MEDIA', 4, _(u'Crawl tweet media and store them')),
    ('STORE_MEDIA', 8, _(u'Crawl tweet media, store them and the tweet too')),

    ('CRAWL_IMAGE', 5, _(u'Crawl & store only tweet images')),
    ('STORE_IMAGE', 10, _(u'Crawl & store tweet images, and the tweet')),

    ('CRAWL_VIDEO', 6, _(u'Crawl & store only tweet videos')),
    ('STORE_VIDEO', 12, _(u'Crawl & store tweet videos, and the tweet')),

    ('CRAWL_ALL', 7, _(u'Crawl anything (articles, media…) and store it')),
    ('STORE_ALL', 14, _(u'Crawl anything, store it, and the tweet too')),
)

TWITTER_MATCH_FIELDS = NamedTupleChoices(
    'TWITTER_MATCH_FIELDS',

    ('TWEET',       1, _(u'Tweet content')),
    ('DATE',        2, _(u'Date')),
    ('LANGUAGE',    3, _(u'Language')),
    ('COORDINATES', 4, _(u'Language')),
    ('CREATOR',     9, _(u'Creator')),

    ('FAVORITES',  20, _(u'Favorites count')),
    ('RETWEETS',   30, _(u'Retweets count')),
    ('MEDIA',      40, _(u'Media')),
    ('URLS',       50, _(u'URLs')),

    ('FAVORITERS', 60, _(u'Favoriters')),
    ('RETWEETERS', 70, _(u'Retweeters')),

    ('MENTIONS',   80, _(u'Mentions')),
    ('HASHTAGS',   90, _(u'Hashtags')),

    ('DESTROYED',  200, _(u'Destroyed')),
)

TWITTER_FINISH_ACTIONS = NamedTupleChoices(
    'TWITTER_FINISH_ACTIONS',
    ('NOTHING', 1, _(u'Let the tweet as is')),
    ('UNSTAR', 2, _(u'Unfavorite the tweet')),
    ('STAR', 3, _(u'Favorite the tweet')),
    ('RETWEET', 4, _(u'Retweet the tweet')),
)

TWITTER_RULES_OPERATION_DEFAULT = RULES_OPERATIONS.ANY
TWITTER_MATCH_TYPE_DEFAULT = TWITTER_MATCH_TYPES.CONTAINS
TWITTER_MATCH_FIELD_DEFAULT = TWITTER_MATCH_FIELDS.TWEET
TWITTER_MATCH_ACTION_DEFAULT = TWITTER_MATCH_ACTIONS.STORE_LINKS
TWITTER_FINISH_ACTION_DEFAULT = TWITTER_FINISH_ACTIONS.NOTHING
TWITTER_RULES_OPERATION_DEFAULT = RULES_OPERATIONS.ANY
TWITTER_GROUP_OPERATION_DEFAULT = RULES_OPERATIONS.ANY

# ——————————————————————————————————————————————————————————————————— Functions


def throttle_fetch_interval(interval, news, mutualized,
                            duplicates, uses_since=None):
    """ Dynamically adapt the fetch interval, given some parameters.

    This allows to fetch more often feeds that produce a lot of new entries,
    and less the ones that do not.

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

        if uses_since:
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
