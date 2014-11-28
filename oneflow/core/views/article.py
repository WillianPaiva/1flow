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

import logging

from random import choice as random_choice

from django.http import HttpResponseBadRequest, HttpResponse

from django.shortcuts import render, get_object_or_404

from ..models import BaseItem  # , Tweet

LOGGER = logging.getLogger(__name__)


def article_content(request, article_id):
    """ Get the article content for displaying to the user. """

    item = get_object_or_404(BaseItem, id=article_id)

    read = request.user.reads.get(item=item)

    if not request.is_ajax():
        return HttpResponseBadRequest('Must be called via Ajax')

    return render(request,
                  'snippets/read/article-content-async.html',
                  {'article': item, 'read': read})


def article_image(request, article_id):
    """ Get the item image for displaying to the user. """

    item = get_object_or_404(BaseItem, id=article_id)

    if hasattr(item, 'image_url'):

        if item.image_url:
            return HttpResponse(item.image_url)

        # BIG FAT WARNING: do not commit until the method gets more love.
        image_url = item.find_image(commit=False)

        if image_url:
            return HttpResponse(image_url)

    else:
        # TODO: implement this for tweets and other item types.
        pass

    numbers    = (1, 2, 3, 4, 5, 6, 7, 8, 9)
    categories = ('abstract', 'animals', 'business', 'cats', 'city', 'food',
                  'nightlife', 'fashion', 'people', 'nature', 'sports',
                  'technics', 'transport')

    tags = set([t.name.lower() for t in item.tags.all()]
               + [t.name.lower() for t in item.feeds.all()[0].tags.all()])

    #
    # HEADS UP: if you change LoremPixel dimensions,
    #           replicate them in _read-list.scss
    #

    try:
        for tag in tags:
            if tag in categories:
                return HttpResponse(
                    u'http://lorempixel.com/g/180/112/{0}/{1}'.format(
                        tag, random_choice(numbers)))

    except:
        LOGGER.exception('Could not do fun things with article/feed tags')

    # This will probably be confusing for the user (category
    # images changes everytime), but is easily fixable.
    return HttpResponse(u'http://lorempixel.com/g/180/112/{0}/{1}'.format(
                        random_choice(categories), random_choice(numbers)))
