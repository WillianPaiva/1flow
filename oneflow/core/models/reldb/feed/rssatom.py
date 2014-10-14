# -*- coding: utf-8 -*-
"""
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

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.db.models.signals import pre_save, post_save, pre_delete

from base import BaseFeed
from ..tag import SimpleTag

LOGGER = logging.getLogger(__name__)

__all__ = [
    'RssAtomFeed',
]


class RssAtomFeed(BaseFeed):

    """ An RSS & Atom feed object. """

    url = models.URLField(unique=True, verbose_name=_(u'url'))

    site_url = models.URLField(
        verbose_name=_(u'web site'), null=True, blank=True,
        help_text=_(u'Website public URL, linked to the globe icon in the '
                    u'source selector. This is not the XML feed URL.'))

    tags = models.ManyToManyField(
        SimpleTag, verbose_name=_(u'tags'),
        help_text=_(u'This tags are used only when articles from this '
                    u'feed have no tags already. They are assigned to new '
                    u'subscriptions too.'))

    # Stored directly from feedparser data to avoid wasting BW.
    last_etag      = models.CharField(verbose_name=_(u'last etag'),
                                      max_length=64, null=True,
                                      blank=True)
    last_modified  = models.CharField(verbose_name=_(u'modified'),
                                      max_length=64, null=True,
                                      blank=True)
