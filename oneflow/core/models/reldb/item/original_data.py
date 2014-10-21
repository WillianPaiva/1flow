# -*- coding: utf-8 -*-
"""
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

import re
import ast

from django.db import models
from django.utils.translation import ugettext_lazy as _

from base import BaseItem
from ..mail_common import email_prettify_raw_message

__all__ = [
    'OriginalData',
]


class OriginalData(models.Model):

    """ Allow to keep any “raw” data associated with a base item.

    The main purpose is to allow later re-processing when technologies
    evolve and permit new attributes to be handled.
    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Original data')
        verbose_name_plural = _(u'Original data')

    article = models.OneToOneField(BaseItem, primary_key=True)

    # This should go away soon, after a full re-parsing.
    google_reader = models.TextField()
    feedparser    = models.TextField()
    raw_email     = models.TextField()

    # These are set to True to avoid endless re-processing.
    google_reader_processed = models.BooleanField(default=False)
    feedparser_processed    = models.BooleanField(default=False)
    raw_email_processed     = models.BooleanField(default=False)

    @property
    def google_reader_hydrated(self):
        """ XXX: should disappear when google_reader_data is useless. """

        if self.google_reader:
            return ast.literal_eval(self.google_reader)

        return None

    @property
    def feedparser_hydrated(self):
        """ XXX: should disappear when feedparser_data is useless. """

        if self.feedparser:
            return ast.literal_eval(re.sub(r'time.struct_time\([^)]+\)',
                                    '""', self.feedparser))

        return None

    @property
    def raw_email_hydrated(self):
        """ XXX: should disappear when raw_email is useless. """

        if self.raw_email:
            return email_prettify_raw_message(self.raw_email)

        return None
