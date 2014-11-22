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
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

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


# —————————————————————————————————————————————————————————————————— Core icons


CORE_CLASSES_ICONS = {

    'RssAtomCreate': 'rss-sign',
    'RssAtomFeed': 'rss',

    'MailAccount': 'inbox',
    'MailFeed': 'envelope',
    'MailFeedRule': 'random',

    'TwitterAccount': 'twitter-sign',
    'TwitterFeed': 'twitter',
    'TwitterFeedRule': 'random',

    'FacebookAccount': 'facebook-sign',
    'FacebookFeed': 'facebook',
    'FacebookFeedRule': 'random',

    'GooglePlusAccount': 'google-plus-sign',
    'GooglePlusFeed': 'google-plus',
    'GooglePlusFeedRule': 'random',

    'Profile': 'user',
    'SyncNode': 'sitemap',
    'HistoryEntry': 'book',
    'SystemStatistics': 'tasks',
}


# ———————————————————————————————————————————————————————————————— Read related


WATCH_ATTRIBUTES_FIELDS_NAMES = (
    'is_fact',
    'is_number',
    'is_analysis',
    'is_quote',
    'is_prospective',
    'is_rules',
    'is_knowhow',
    'is_knowledge',
    'is_fun',
)

READ_STATUS_DATA = {
    #
    # NOTE 1: "is_good" has nothing to do here, it's a system flag.
    #       do not confuse it with read statuses.
    #
    # NOTE 2: These two are not real statuses, but having them here
    #       allows to keep everything status-related here, without
    #       needing to craft specific code outside of this file.
    #       Just do something like:
    #
    #           if mode == 'is_read' and negated:
    #               mode = 'is_unread'
    #
    #       And then use `mode` as usual, like any other.
    #

    'all': {
        'list_headers':  (_(u'%(count)s article'),
                          _(u'%(count)s articles')),
    },

    'is_unread': {
        'list_headers':  (_(u'%(count)s unread article'),
                          _(u'%(count)s unread articles')),
    },

    # —————————————————————————————————————————————————————————————————————

    'is_read': {
        'list_name':     pgettext_lazy(u'past participle, plural', u'read'),
        'view_name':     u'read',
        'list_url':      _(ur'^read/read/$'),
        'do_title':      _(u'Mark as read'),
        'list_headers':  (_(u'%(count)s read article'),
                          _(u'%(count)s read articles')),
        'undo_title':    _(u'Mark as unread'),
        'do_label':      _(u'Mark read'),
        'undo_label':    _(u'Mark unread'),
        'status_label':  pgettext_lazy(u'adjective', u'read'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'check-empty'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name', u'check'),
    },

    'is_starred': {
        'list_name':     _(u'starred'),
        'view_name':     u'starred',
        'list_url':      _(ur'^read/starred/$'),
        'do_title':      _(u'Star (add to favorites)'),
        'list_headers':  (_(u'%(count)s starred article'),
                          _(u'%(count)s starred articles')),
        'undo_title':    _(u'Remove from starred/favorites'),
        'do_label':      pgettext_lazy(u'verb', u'Star'),
        'undo_label':    _(u'Unstar'),
        'status_label':  _(u'starred'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'star-empty'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name', u'star'),
    },

    'is_archived': {
        'list_name':     _(u'archived'),
        'view_name':     u'archived',
        'list_url':      _(ur'^read/archived/$'),
        'do_title':      _(u'Archive'),
        'list_headers':  (_(u'%(count)s article archived'),
                          _(u'%(count)s articles archived')),
        'undo_title':    _(u'Delete'),
        'do_label':      _(u'Archive'),
        'undo_label':    _(u'Delete'),
        'status_label':  _(u'archived'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'download'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'archive'),
    },

    'is_bookmarked': {
        'list_name':     _(u'later'),
        'view_name':     u'later',
        'list_url':      _(ur'^read/later/$'),
        'do_title':      _(u'Keep for reading later'),
        'list_headers':  (_(u'%(count)s article to read later'),
                          _(u'%(count)s articles to read later')),
        'undo_title':    _(u'Remove from reading list'),
        'do_label':      _(u'Read later'),
        'undo_label':    _(u'Do not read later'),
        'status_label':  _(u'kept for later'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'bookmark-empty'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'bookmark'),
    },

    'is_fact': {
        'list_name':     _(u'facts'),
        'view_name':     u'facts',
        'list_url':      _(ur'^read/facts/$'),
        'do_title':      _(u'Mark as fact / important event'),
        'list_headers':  (_(u'%(count)s article containing fact(s)'),
                          _(u'%(count)s articles containing fact(s)')),
        'undo_title':    _(u'Remove from facts / important events'),
        'status_title':  _(u'This article contains one or '
                           u'more important facts'),
        'do_label':      _(u'Mark as fact'),
        'undo_label':    _(u'Unmark fact'),
        'status_label':  _(u'fact'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'circle-blank'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'bullseye'),
    },

    'is_number': {
        'list_name':     _(u'numbers'),
        'view_name':     u'numbers',
        'list_url':      _(ur'^read/numbers/$'),
        'do_title':      _(u'Mark as valuable number'),
        'list_headers':  (_(u'%(count)s article containing number(s)'),
                          _(u'%(count)s articles containing number(s)')),
        'undo_title':    _(u'Remove from valuable numbers'),
        'status_title':  _(u'This article contains quantified '
                           u'numbers for a watch.'),
        'do_label':      _(u'Mark as number'),
        'undo_label':    _(u'Unmark number'),
        'status_label':  _(u'number'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'bar-chart'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'bar-chart icon-flip-horizontal'),
        'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                       u'bar-chart'),
        # 'undo_icon_stack': True,
    },

    'is_analysis': {
        'list_name':     _(u'analysis'),
        'view_name':     u'analysis',
        'list_url':      _(ur'^read/analysis/$'),
        'do_title':      _(u'Mark as analysis / study / research'),
        'list_headers':  (pgettext_lazy(u'singular', u'%(count)s analysis'),
                          pgettext_lazy(u'plural', u'%(count)s analysis')),
        'undo_title':    _(u'Unmark analysis / study / research'),
        'status_title':  _(u'This article contains an analysis, '
                           u'an in-depth study or a research '
                           u'publication.'),
        'do_label':      _(u'Mark as analysis'),
        'undo_label':    _(u'Unmark analysis'),
        'status_label':  _(u'analysis'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'beaker'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'beaker icon-rotate-90'),
        'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                       u'beaker'),
    },

    'is_quote': {
        'list_name':     _(u'quotes'),
        'view_name':     u'quotes',
        'list_url':      _(ur'^read/quotes/$'),
        'do_title':      _(u'Mark as containing quote(s) from people '
                           u'you consider important'),
        'list_headers':  (_(u'%(count)s article containing quote(s)'),
                          _(u'%(count)s articles containing quote(s)')),
        'undo_title':    _(u'Unmark as containing quotes '
                           u'(people are not famous anymore?)'),
        'status_title':  _(u'This article contains one or more quote '
                           u'from people you care about.'),
        'do_label':      _(u'Mark as quote'),
        'undo_label':    _(u'Unmark quote'),
        'status_label':  pgettext_lazy(u'noun', u'quote'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'quote-left icon-flip-vertical'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'quote-right'),
        'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                       u'quote-left icon-flip-vertical'),
    },

    'is_prospective': {
        'list_name':     _(u'prospective'),
        'view_name':     u'prospective',
        'list_url':      _(ur'^read/prospective/$'),
        'do_title':      _(u'Mark as prospective-related content'),
        'list_headers':  (_(u'%(count)s prospective article'),
                          _(u'%(count)s prospective articles')),
        'undo_title':    _(u'Unmark as prospective-related content'),
        'status_title':  _(u'This article contains prospective element(s) '
                           u'or must-remember hypothesis.'),
        'do_label':      _(u'Mark as prospective'),
        'undo_label':    _(u'Unmark prospective'),
        'status_label':  _(u'prospective'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'lightbulb'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'lightbulb icon-rotate-180'),
        'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                       u'lightbulb'),
    },

    'is_rules': {
        'list_name':     _(u'rules'),
        'view_name':     u'rules',
        'list_url':      _(ur'^read/rules/$'),
        'do_title':      _(u'Mark as legal/regulations-related content'),
        'list_headers':  (_(u'%(count)s regulation-related article'),
                          _(u'%(count)s regulation-related articles')),
        'undo_title':    _(u'Unmark as legal content (overriden laws?)'),
        'status_title':  _(u'This article contains regulations/'
                           u'law/rules element(s)'),
        'do_label':      _(u'Mark as law/regul.'),
        'undo_label':    _(u'Unmark law/regul.'),
        'status_label':  _(u'regulations'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'legal icon-flip-horizontal'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'legal icon-rotate-180'),
        'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                       u'legal icon-flip-horizontal'),
    },

    'is_knowhow': {
        'list_name':    _(u'best-practices'),
        # WARNING: there  is a '_' in the view name, and a '-' in the URL.
        'view_name':     u'know_how',
        'list_url':      _(ur'^read/best-practices/$'),
        'do_title':      _(u'Mark as best-practices / state of art '
                           u'content'),
        'list_headers':  (_(u'%(count)s best-practices article'),
                          _(u'%(count)s best-practices articles')),
        'undo_title':    _(u'Unmark as best-practices / state of art '
                           u'(has it become obsolete?)'),
        'status_title':  _(u'This article contains best-practices / '
                           u' state of art element(s).'),
        'do_label':      _(u'Mark as best-practice'),
        'undo_label':    _(u'Unmark best-practice'),
        'status_label':  pgettext_lazy(u'noun', u'know-how'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name',
                                       u'trophy'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'trophy icon-flip-vertical'),
        'status_icon':   pgettext_lazy(u'awesome-font icon name',
                                       u'trophy'),
    },

    'is_knowledge': {
        'list_name':     _(u'knowlegde'),
        'view_name':     u'knowledge',
        'list_url':      _(ur'^read/knowledge/$'),
        'do_title':      _(u'Mark as a valuable piece of '
                           u'knowlegde for your brain or life'),
        'list_headers':  (_(u'%(count)s knowledge article'),
                          _(u'%(count)s knowledge articles')),
        'undo_title':    _(u'Unmark as neuronal-exciting '
                           u'element(s)'),
        'status_title':  _(u'This article contains a valuable '
                           u'piece of knowlegde.'),
        'do_label':      _(u'Mark as Knowledge'),
        'undo_label':    _(u'Unmark knowlegde'),
        'status_label':  _(u'knowledge'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name', u'globe'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name',
                                       u'globe icon-rotate-180'),
        'status_icon':   pgettext_lazy(u'awesome-font icon name', u'globe'),
    },

    'is_fun': {
        'list_name':     _(u'funbox'),
        'view_name':     u'fun',
        'list_url':      _(ur'^read/fun/$'),
        'do_title':      _(u'Mark as being fun. Are you sure?'),
        'list_headers':  (_(u'%(count)s fun article'),
                          _(u'%(count)s fun articles')),
        'undo_title':    _(u'Not fun anymore, sadly.'),
        'status_title':  _(u'OMG, this thing is sooooooooo fun! LMAO!'),
        'do_label':      _(u'Mark as fun'),
        'undo_label':    _(u'Mark as boring'),
        'status_label':  _(u'fun'),
        'do_icon':       pgettext_lazy(u'awesome-font icon name', u'smile'),
        'undo_icon':     pgettext_lazy(u'awesome-font icon name', u'frown'),
        'status_icon':   pgettext_lazy(u'awesome-font icon name', u'smile'),
    },
}


# ——————————————————————————————————————————————————————————————————— Functions


def lowername(objekt):
    """ return the ``name`` attribute of :param:`object`, lowered(). """

    return attrgetter('name')(objekt).lower()
