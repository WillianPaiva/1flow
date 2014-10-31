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
import logging

from statsd import statsd

from django.db import models
from django.utils.translation import ugettext_lazy as _

from oneflow.base.utils import register_task_method

from ..common import ORIGINS, CONTENT_TYPES
from ..mail_common import email_prettify_raw_message
from ..tag import SimpleTag as Tag
from ..author import Author

from base import BaseItem

LOGGER = logging.getLogger(__name__)


__all__ = [
    'OriginalData',

    # Tasks will be added from below.
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

    item = models.OneToOneField(BaseItem, primary_key=True,
                                related_name='original_data')

    # This should go away soon, after a full re-parsing.
    google_reader = models.TextField()
    feedparser    = models.TextField()
    raw_email     = models.TextField()

    # These are set to True to avoid endless re-processing.
    google_reader_processed = models.BooleanField(default=False)
    feedparser_processed    = models.BooleanField(default=False)
    raw_email_processed     = models.BooleanField(default=False)

    def __unicode__(self):
        return u'Original data for {0}'.format(self.item)

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


# ———————————————————————————————————————————————————————————— External methods


def BaseItem_add_original_data_method(self, name, value, commit=True):
    """ Direct property writer for an original data. """

    try:
        od = self.original_data

    except OriginalData.DoesNotExist:
        od = OriginalData(item=self)

    setattr(od, name, value)

    if commit:
        od.save()

    return od


def BaseItem_remove_original_data_method(self, name, commit=True):
    """ Direct property remover for an original data. """

    try:
        od = self.original_data

    except OriginalData.DoesNotExist:
        return

    try:
        delattr(od, name)

    except AttributeError:
        pass

    else:
        if commit:
            od.save()


def BaseItem_postprocess_original_data_method(self, force=False, commit=True):
    """ Generic method for original data post_processing. """

    methods_table = {
        ORIGINS.NONE: self.postprocess_guess_original_data,
        ORIGINS.FEEDPARSER: self.postprocess_feedparser_data,
    }

    meth = methods_table.get(self.origin, None)

    if meth is None:
        LOGGER.warning(u'No method to post-process origin type %s of '
                       u'article %s.', self.origin, self)
        return

    meth(force=force, commit=commit)


def BaseItem_postprocess_guess_original_data_method(self, force=False,
                                                    commit=True):

    need_save = False

    if self.original_data.feedparser_hydrated:
        self.origin = ORIGINS.FEEDPARSER
        need_save   = True

    elif self.original_data.google_reader_hydrated:
        self.origin = ORIGINS.GOOGLE_READER
        need_save   = True

    if need_save:
        if commit:
            self.save()

        # Now that we have an origin type, re-run the real post-processor.
        self.postprocess_original_data(force=force, commit=commit)


def BaseItem_postprocess_feedparser_data_method(self, force=False,
                                                commit=True):
    """ XXX: should disappear when feedparser_data is useless. """

    if self.original_data.feedparser_processed and not force:
        LOGGER.info('feedparser data already post-processed.')
        return

    fpod = self.original_data.feedparser_hydrated

    if fpod:
        if self.tags == [] and 'tags' in fpod:
            tags = list(
                Tag.get_tags_set((
                    t['term']
                    # Sometimes, t['term'] can be None.
                    # http://dev.1flow.net/webapps/1flow/group/4082/
                    for t in fpod['tags'] if t['term'] is not None),
                    origin=self))

            self.update_tags(tags, initial=True, need_reload=False)

        if self.authors == []:
            Author.get_authors_from_feedparser_article(fpod,
                                                       set_to_article=self)

        if self.language is None:
            language = fpod.get('summary_detail', {}).get('language', None)

            if language is None:
                language = fpod.get('title_detail', {}).get(
                    'language', None)

            if language is not None:
                try:
                    self.language = language.lower()
                    self.save()

                except:
                    # This happens if the language code of the
                    # feedparser data does not correspond to a
                    # Django setting language we support.
                    LOGGER.exception(u'Cannot set language %s on '
                                     u'article %s.', language, self)

        if self.is_orphaned:
            # We have a chance to get at least *some* content. It will
            # probably be incomplete, but this is better than nothing.

            detail = fpod.get('summary_detail', {})

            if detail:
                detail_type = detail.get('type', None)
                detail_value = detail.get('value', '')

                # We need some *real* data, though
                if len(detail_value) > 20:

                    if detail_type == 'text/plain':
                        self.content = detail_value
                        self.content_type = CONTENT_TYPES.MARKDOWN
                        self.save()

                        statsd.gauge('articles.counts.markdown',
                                     1, delta=True)

                    elif detail_type == 'text/html':
                        self.content = detail_value
                        self.content_type = CONTENT_TYPES.HTML
                        self.save()

                        statsd.gauge('articles.counts.html',
                                     1, delta=True)

                        self.convert_to_markdown()

                    else:
                        LOGGER.warning(u'No usable content-type found '
                                       u'while trying to recover article '
                                       u'%s content: %s => "%s".', self,
                                       detail_type, detail_value)
                else:
                    LOGGER.warning(u'Empty (or nearly) content-type '
                                   u'found while trying to recover '
                                   u'orphaned article %s '
                                   u'content: %s => "%s".', self,
                                   detail_type, detail_value)
            else:
                LOGGER.warning(u'No summary detail found while trying '
                               u'to recover orphaned article %s '
                               u'content.', self)

        if self.comments_feed_url is None:

            comments_feed_url = fpod.get('wfw_commentrss', None)

            if comments_feed_url:
                self.comments_feed_url = comments_feed_url
                self.save()

        # We don't care anymore, it's already in another database.
        # self.offload_attribute('feedparser_original_data')

    self.original_data.feedparser_processed = True
    self.original_data.save()

def BaseItem_postprocess_google_reader_data_method(self, force=False,
                                                   commit=True):

    LOGGER.warning(u'postprocess_google_reader_data() is not implemented '
                   u'yet but it was called for article %s!', self)


BaseItem.add_original_data               = \
    BaseItem_add_original_data_method
BaseItem.remove_original_data            = \
    BaseItem_remove_original_data_method
BaseItem.postprocess_original_data       = \
    BaseItem_postprocess_original_data_method
BaseItem.postprocess_guess_original_data = \
    BaseItem_postprocess_guess_original_data_method
BaseItem.postprocess_feedparser_data     = \
    BaseItem_postprocess_feedparser_data_method
BaseItem.postprocess_google_reader_data  = \
    BaseItem_postprocess_google_reader_data_method


# HEADS UP: we need to register against BaseItem, because OriginalData
#           cannot .objects.get() an Article in register_task_method().
register_task_method(BaseItem, BaseItem.postprocess_original_data,
                     globals(), queue=u'low')
