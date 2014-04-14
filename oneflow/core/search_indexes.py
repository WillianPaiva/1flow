# -*- coding: utf-8 -*-
"""
    Copyright 2014 Olivier Cortès <oc@1flow.io>

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

#import logging
from itertools import chain

from haystack import indexes
from models import Article


class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
    """

        Worth a read for starting: http://stackoverflow.com/q/18338898/654755
    """

    title = indexes.CharField(model_attr='title')
    text = indexes.CharField(document=True, use_template=True)
    author = indexes.CharField(model_attr='user')
    date_published = indexes.DateTimeField(model_attr='date_published')
    tags = indexes.MultiValueField(faceted=True)  # m2m field

    # Used for auto-completion.
    title_autocomplete = indexes.EdgeNgramField(model_attr='title')

    def get_model(self):
        return Article

    def prepare_tags(self, obj):
        """ Rassemble tags from the article reads, which can be different
            from the “bare” article tags if readers customized them. """

        return set(tag.name for tag in chain(
                   *(read.tags for read in self.reads)))

    #def index_queryset(self, using=None):
    #    """Used when the entire index for model is updated."""
    #    return self.get_model().objects.filter(
    #    pub_date__lte=datetime.datetime.now())

    #weight = indexes.MultiValueField(faceted=True, null=True)

