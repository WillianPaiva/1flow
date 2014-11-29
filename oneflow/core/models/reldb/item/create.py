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

from django.conf import settings

from ..common import ORIGINS

from article import create_article_from_url
from tweet import create_tweet_from_id

LOGGER = logging.getLogger(__name__)


__all__ = [
    'create_item_from_url',
]


def handle_special_urls(url, feeds, origin):
    """ See if an URL deserves a special processing or not.

    Eg.:

    - a 1flow URL will redirect to the Read, directly.
    - a twitter status URL will create a tweet, not an article.
    - etc (things WILL be added over time).
    """

    if settings.SITE_DOMAIN in url:
        # The following code should not fail, because the URL has
        # already been idiot-proof-checked in core.forms.selector
        #   .WebPagesImportForm.validate_url()
        read_id = url[-26:].split('/', 1)[1].replace('/', '')

        # Avoid an import cycle.
        from .read import Read

        # HEADS UP: we just patch the URL to benefit from all the
        # Article.create_article() mechanisms (eg. mutualization, etc).
        url = Read.objects.get(id=read_id).item.url

        return url

    if u'//twitter.com/' in url and u'/status/' in url:

        if u'/photo/' in url:
            LOGGER.error(u'Implement Twitter photo status handling (from %s)',
                         url)
            raise NotImplementedError(u'Implement Twitter status photos…')

        return create_tweet_from_id(int(url.rsplit('/', 1)[-1]),
                                    feeds,
                                    origin)

    return None


def create_item_from_url(url, feeds=None, origin=None):
    """ Create an article from a web url. """

    if feeds is None:
        feeds = []

    elif not hasattr(feeds, '__iter__'):
        feeds = [feeds]

    if origin is None:
        origin = ORIGINS.WEBIMPORT

    result = handle_special_urls(url, feeds, origin)

    if result is not None:
        if isinstance(result, str) or isinstance(result, unicode):
            url = result

        else:
            return result

    return create_article_from_url(url, feeds, origin)
