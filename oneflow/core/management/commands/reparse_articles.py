# -*- coding: utf-8 -*-
u"""
Copyright 2015 Olivier Cortès <oc@1flow.io>.

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
# import simplejson as json

from django.core.management.base import BaseCommand

from oneflow.core.models import WebSite, Article

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):

    """ Reparse one or more articles of a given website. """

    args = u'<website url or ID> [test]'
    help = (
        u'Reparse one or more articles of a given website. If test is '
        u'anything (eg "test", 1, whatever not None), only one article '
        u'will be converted in verbose mode, and its content will be '
        u'printed afterwise for you to see if it went good or not.'
    )

    def handle(self, *args, **options):
        """ Deserialize the objects, Luke. """

        website = None
        test = False

        for arg in args:
            if website is None:
                if arg.isdigit():
                    website = WebSite.objects.get(id=int(arg))
                else:
                    website = WebSite.objects.get_from_url(arg)
            else:
                test = True

        articles = Article.objects.filter(
            url__startswith=website.url).filter(duplicate_of_id=None)

        if test:
            articles = articles.order_by('?')[:1]

        else:
            LOGGER.info(u'Re-processing %s articles…', articles.count())
            articles = articles.order_by('-date_created')

        total_count = 0
        failed_count = 0

        for article in articles:
            url_absolute = article.url_absolute
            is_orphaned = article.is_orphaned

            redo = not url_absolute

            try:
                article.reset(force=True)

                if redo:
                    article.absolutize_url()

                else:
                    article.url_absolute = url_absolute
                    article.is_orphaned = is_orphaned

                article.fetch_content(verbose=test)

            except:
                LOGGER.exception(u'Could not fetch article %s', article)
                failed_count += 1

            else:
                LOGGER.info(u'Succesfully fetched %s.', article)
                total_count += 1

        if test:
            LOGGER.info(u'Article content: \n\n%s', article.content)

        else:
            LOGGER.info(u'Re-fetched %s articles from %s (failed: %s).',
                        total_count, website, failed_count)
