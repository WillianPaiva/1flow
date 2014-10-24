# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

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


from bs4 import BeautifulSoup
# from constance import config
from jsonfield import JSONField

# from xml.sax import SAXParseException

# from humanize.time import naturaldelta
# from humanize.i18n import django_language

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

# from oneflow.base.utils import register_task_method
# from oneflow.base.utils.http import clean_url
# from oneflow.base.utils.dateutils import now

from ..common import (
    CONTENT_TYPES,
    CONTENT_TYPES_FINAL,
    CONTENT_PREPARSING_NEEDS_GHOST,
    CONTENT_FETCH_LIKELY_MULTIPAGE,
    ORIGINS,
    REQUEST_BASE_HEADERS,
)


LOGGER = logging.getLogger(__name__)


__all__ = [
    'MultiPagesUrlItem',

    # tasks will be added by register_task_method()
]


# ——————————————————————————————————————————————————————————————————— end ghost


class MultiPagesUrlItem(models.Model):

    """ Abstract Item that knows how to handle multiple pages URL. """

    class Meta:
        abstract = True
        app_label = 'core'
        verbose_name = _(u'Multi-page URLs item')
        verbose_name_plural = _(u'Multi-page URLs items')

    pages_url = JSONField(default=list, verbose_name=_(u'Pages URLs'))

    # ————————————————————————————————————————————————————————————————— Methods

    def likely_multipage_content(self):

        for feed in self.feeds:
            try:
                website = feed.website

            except:
                continue

            if website.has_option(CONTENT_FETCH_LIKELY_MULTIPAGE):
                return True

            if feed.has_option(CONTENT_FETCH_LIKELY_MULTIPAGE):
                return True

        return False

    def get_next_page_link(self, html_data):
        """ Try to find a “next page” link in the partial content given as
            parameter. """

        # soup = BeautifulSoup(html_data)

        return None
