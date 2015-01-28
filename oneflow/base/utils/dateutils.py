# -*- coding: utf-8 -*-
u""" Global timezone aware functions.

____________________________________________________________________

Copyright 2012-2014 Olivier Cortès <oc@1flow.io>

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

import dateutil.parser
import dateutil.tz

from email.utils import (
    mktime_tz as email_utils_mktime_tz,
    parsedate_tz as email_utils_parsedate_tz,
)
import time as pytime
import datetime as pydatetime
from humanize.i18n import django_language
import humanize.time as humanize_time

from django.conf import settings
from django.utils.timezone import (is_aware, is_naive,  # NOQA
                                   make_aware, utc,
                                   now as dj_now)

LOGGER = logging.getLogger(__name__)


__all__ = ('today', 'timedelta', 'naturaltime', 'naturaldelta',
           'now', 'ftstamp', 'tzcombine', 'combine', 'time', 'datetime',
           'is_aware', 'is_naive',
           'until_tomorrow_delta', 'stats_datetime', 'benchmark',
           'pytime', 'pydatetime', 'email_date_to_datetime_tz',
           'twitter_datestring_to_datetime_utc',
           'dateutilDateHandler', 'datetime_from_feedparser_entry', )

# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Local aliases


dt_combine       = pydatetime.datetime.combine
dt_fromtimestamp = pydatetime.datetime.fromtimestamp


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Naive aliases


today     = pydatetime.date.today
timedelta = pydatetime.timedelta


def naturaltime(*args, **kwargs):
    """ Wrap `humanize.naturaltime` into django_language(). """

    with django_language():
        return humanize_time.naturaltime(*args, **kwargs)


def naturaldelta(*args, **kwargs):
    """ Wrap `humanize.naturaldelta` into django_language(). """

    with django_language():
        return humanize_time.naturaldelta(*args, **kwargs)


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Aware aliases


if settings.USE_TZ:
    now       = dj_now
    ftstamp   = lambda x: dt_fromtimestamp(x, utc)
    tzcombine = lambda x, y: make_aware(dt_combine(x, y), utc)
    time      = lambda *args: pydatetime.time(*args, tzinfo=utc)
    datetime  = lambda *args: pydatetime.datetime(*args, tzinfo=utc)

else:
    now       = pydatetime.datetime.now
    ftstamp   = dt_fromtimestamp
    tzcombine = dt_combine
    time      = pydatetime.time
    datetime  = pydatetime.datetime

combine  = dt_combine


# ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••• functions


def until_tomorrow_delta(time_of_tomorrow=None):
    """ Get a delta of time until next day.

    .. note:: This should probably go to ``oneflow.base.something``.
    """

    tomorrow = today() + timedelta(days=1)

    if time_of_tomorrow is None:
        time_of_tomorrow = time(0, 0, 0)

    return combine(tomorrow, time_of_tomorrow) - now()


def stats_datetime():
    """ Generate a string from now, suitable for benchmark() calls. """

    return pytime.strftime('%Y-%m-%d %H:%M')


class benchmark(object):

    """ Simple benchmark context-manager class.

    http://dabeaz.blogspot.fr/2010/02/context-manager-for-timing-benchmarks.html  # NOQA
    """

    def __init__(self, name=None):
        """ Oh my, pep257, this is an init method. """

        self.name = name or u'Generic benchmark'

    def __enter__(self):
        """ Start the timer. """

        self.start   = pytime.time()
        self.dtstart = stats_datetime()

    def __exit__(self, ty, val, tb):
        """ Stop the timer and display a logging message with elapsed time. """

        LOGGER.info("%s started %s, ran in %s.", self.name, self.dtstart,
                    naturaldelta(pytime.time() - self.start))
        return False


def email_date_to_datetime_tz(email_date):
    u""" Return a datetime with TZ from an email “Date:” field.

    Cf. http://stackoverflow.com/a/8339750/654755

    Alternative to look at if problems:
    http://stackoverflow.com/a/12160056/654755
    """

    msg_datetime = None

    if email_date:
        date_tuple = email_utils_parsedate_tz(email_date)

        if date_tuple:
            msg_datetime = pydatetime.datetime.fromtimestamp(
                email_utils_mktime_tz(date_tuple))

    return msg_datetime


def twitter_datestring_to_datetime_utc(twitter_datestring):
    """ Return a datetime from a twitter date string. """

    time_tuple = email_utils_parsedate_tz(twitter_datestring.strip())

    dt = datetime(*time_tuple[:6])

    return dt - timedelta(seconds=time_tuple[-1])


def dateutilDateHandler(aDateString):
    """ Custom date handler.

    See issue https://code.google.com/p/feedparser/issues/detail?id=404
    """

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


def datetime_from_feedparser_entry(feedparser_article):
    """ Return a datetime, if possible, from a feedparser entry.

    If not possible, return None.

    If the datetime is naive, it will be converted
    to an UTC timezone-aware datetime.
    """

    the_datetime = None

    if feedparser_article.published_parsed:
        try:
            the_datetime = datetime(*feedparser_article.published_parsed[:6])

        except:
            pass

    if the_datetime is None and feedparser_article.published:
        try:
            the_datetime = datetime(
                *dateutilDateHandler(feedparser_article.published)[:6])
        except:
            pass

    if the_datetime is not None:
        # This is probably a half-false assumption, but have currently no
        # simple way to get the timezone from the feedparser entry. Anyway,
        # we *need* an offset aware for later comparisons. BTW, in most
        # cases, feedparser already did a good job before reaching here.
        if is_naive(the_datetime):
            the_datetime = make_aware(the_datetime, utc)

    return the_datetime
