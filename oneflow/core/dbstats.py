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

from statsd import statsd
# from constance import config

from oneflow.core.models import (
    SimpleTag as Tag,
    BaseFeed, Subscription,
    Article,
    Author,
    WebSite,
    Read,
    CONTENT_TYPES,
)
from oneflow.base.utils.dateutils import benchmark


LOGGER = logging.getLogger(__name__)


__all__ = [
    'synchronize_statsd_articles_gauges',
    'synchronize_statsd_tags_gauges',
    'synchronize_statsd_websites_gauges',
    'synchronize_statsd_authors_gauges',
    'synchronize_statsd_feeds_gauges',
    'synchronize_statsd_subscriptions_gauges',
    'synchronize_statsd_reads_gauges',
]


def synchronize_statsd_articles_gauges(full=False):
    """ synchronize all articles-related gauges on our statsd server. """

    with benchmark('synchronize statsd gauges for Article.*'):

        empty               = Article.objects.empty()
        # empty_pending       = empty.filter(content_error='', url_error='')
        # empty_content_error = empty.filter(content_error__ne='')
        # empty_url_error     = empty.filter(url_error__ne='')

        parsed             = Article.objects.parsed()
        html               = parsed.filter(content_type=CONTENT_TYPES.HTML)
        markdown           = parsed.filter(content_type=CONTENT_TYPES.MARKDOWN)

        absolutes          = Article.objects.absolute()
        duplicates         = Article.objects.duplicate()
        orphaned           = Article.objects.orphaned().master()
        content_errors     = Article.objects.exclude(content_error=None)
        url_errors         = Article.objects.exclude(url_error=None)

        with statsd.pipeline() as spipe:
            spipe.gauge('articles.counts.total',
                        Article.objects.all().count())
            spipe.gauge('articles.counts.markdown', markdown.count())
            spipe.gauge('articles.counts.html', html.count())
            spipe.gauge('articles.counts.empty', empty.count())
            spipe.gauge('articles.counts.content_errors',
                        content_errors.count())
            spipe.gauge('articles.counts.url_errors', url_errors.count())

            if full:
                spipe.gauge('articles.counts.orphaned', orphaned.count())
                spipe.gauge('articles.counts.absolutes', absolutes.count())
                spipe.gauge('articles.counts.duplicates', duplicates.count())


def synchronize_statsd_tags_gauges(full=False):
    """ synchronize all tag-related gauges on our statsd server. """

    with benchmark('synchronize statsd gauges for Tag.*'):

        statsd.gauge('tags.counts.total', Tag.objects.all().count())

        if full:
            duplicates = Tag.objects.exclude(duplicate_of=None)
            statsd.gauge('tags.counts.duplicates', duplicates.count())


def synchronize_statsd_websites_gauges(full=False):
    """ synchronize all website-related gauges on our statsd server. """

    with benchmark('synchronize statsd gauges for WebSite.*'):

        statsd.gauge('websites.counts.total', WebSite.objects.all().count())

        if full:
            duplicates = WebSite.objects.exclude(duplicate_of=None)
            statsd.gauge('websites.counts.duplicates', duplicates.count())


def synchronize_statsd_authors_gauges(full=False):
    """ synchronize all author-related gauges on our statsd server. """

    with benchmark('synchronize statsd gauges for Author.*'):

        statsd.gauge('authors.counts.total', Author.objects.all().count())

        if full:
            duplicates = Author.objects.exclude(duplicate_of=None)
            statsd.gauge('authors.counts.duplicates', duplicates.count())


def synchronize_statsd_feeds_gauges(full=False):
    """ synchronize all feed-related gauges on our statsd server. """

    with benchmark('synchronize statsd gauges for BaseFeed.*'):

        statsd.gauge('feeds.counts.total', BaseFeed.objects.all().count())
        statsd.gauge('feeds.counts.open', BaseFeed.objects.active().count())

        if full:
            duplicates = BaseFeed.objects.exclude(duplicate_of=None)
            statsd.gauge('feeds.counts.duplicates', duplicates.count())

        # TODO: stats by Feed type (email, rss, twitter…)
        pass


def synchronize_statsd_subscriptions_gauges(full=False):
    """ synchronize all subscription-related gauges on our statsd server. """

    with benchmark('synchronize statsd gauges for Subscription.*'):

        statsd.gauge('subscriptions.counts.total',
                     Subscription.objects.all().count())


def synchronize_statsd_reads_gauges(full=False):
    """ synchronize all read-related gauges on our statsd server. """

    with benchmark('synchronize statsd gauges for Read.*'):

        count = Read.objects.all().count()
        good = Read.objects.good().count()
        bad = Read.objects.bad().count()

        with statsd.pipeline() as spipe:
            spipe.gauge('reads.counts.total', count)
            spipe.gauge('reads.counts.good', good)
            spipe.gauge('reads.counts.bad', bad)

        # Am I paranoïd?!? No, I come from two years of MongoDB.
        # Sorry PostgreSQL, I'm underway healing.
        if bad != (count - good):
            LOGGER.warning(u'Bad count (%s) is different from total-good (%s)!',
                           bad, count - good)
