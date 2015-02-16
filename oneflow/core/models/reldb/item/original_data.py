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
import json
import logging

from statsd import statsd

from django.db import models
from django.utils.translation import ugettext_lazy as _

from oneflow.base.utils import register_task_method
from oneflow.base.utils.dateutils import (
    twitter_datestring_to_datetime_utc,
    datetime_from_feedparser_entry,
)

from ..common import ORIGINS, CONTENT_TYPES
from ..account.common import email_prettify_raw_message
from ..tag import SimpleTag as Tag
from ..language import Language
from ..author import Author

from base import BaseItem
from tweet import Tweet

LOGGER = logging.getLogger(__name__)


__all__ = [
    'OriginalData',

    # Tasks will be added from below.
]


class OriginalDataReprocessException(Exception):

    """ raised when an origin has been found on an item that hadn't one. """

    pass


class OriginalDataStopProcessingException(Exception):

    """ raised when we want to abort post-processing for any reason. """

    pass


class OriginalDataIncompatibleException(Exception):

    """ raised when an origin doesn't match the item content.

    Happens when an article is fetched from the internet, originating
    from a tweet entities field. Origin is TWITTER but item is an Article,
    we should not post-process anything, this will not work.

    This particular situation should be investigated later.
    """

    pass


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
    google_reader = models.TextField(null=True, blank=True)
    feedparser    = models.TextField(null=True, blank=True)
    raw_email     = models.TextField(null=True, blank=True)
    twitter       = models.TextField(null=True, blank=True)
    # webimport     = models.TextField(null=True, blank=True)

    # These are set to True to avoid endless re-processing.
    google_reader_processed = models.BooleanField(default=False)
    feedparser_processed    = models.BooleanField(default=False)
    raw_email_processed     = models.BooleanField(default=False)
    twitter_processed       = models.BooleanField(default=False)
    # webimport_processed     = models.BooleanField(default=False)

    def __unicode__(self):
        return u'Original data for {0}'.format(self.item)

    @property
    def is_processed(self):
        """ Tells if all original data have been processed at least once. """

        for attr_name in (
            'google_reader',
            'feedparser',
            'raw_email',
            'twitter',
            #  'webimport',
        ):

            if getattr(self, attr_name, None) \
                    and not getattr(self, attr_name + '_processed'):
                return False

        return True

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

    @property
    def twitter_hydrated(self):
        """ Hydrate via JSON. """

        return json.loads(self.twitter)

    @property
    def webimport_hydrated(self):
        """ Hydrate via direct return. """

        return None
        return self.webimport

# ———————————————————————————————————————————————————————————— External methods


def BaseItem_add_original_data_method(self, name, value, launch_task=False,
                                      apply_now=False, commit=True):
    """ Direct property writer for an original data.

    Launches the post-processor celery task if told so. Else, it is the
    responsibility of the caller (or the programmer) to do it somewhere.
    """

    # self_name = self._meta.verbose_name
    self_id = self.id

    try:
        od = self.original_data

    except OriginalData.DoesNotExist:
        od = OriginalData(item=self)

    if getattr(od, name, None) == value:
        LOGGER.warning(u'Not re-setting original data on %s!', self)

    else:
        setattr(od, name, value)

        if commit:
            # with transaction.atomic():
            od.save()

        if launch_task:

            the_task = globals()['baseitem_postprocess_original_data_task']

            if apply_now:
                the_task.apply((self_id, ))

            else:
                the_task.delay(self_id)

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


def BaseItem_postprocess_original_data_method(self, force=False,
                                              commit=True, first_run=True):
    """ Generic method for original data post_processing. """

    self_name = self._meta.verbose_name
    self_id = self.id

    if self.duplicate_of_id:
        LOGGER.warning(u'Not post-processing original data of duplicate '
                       u'%s %s.', self_name, self_id)
        return
        # raise OriginalDataStopProcessingException

    methods_table = {
        None: self.postprocess_guess_original_data,
        ORIGINS.NONE: self.postprocess_guess_original_data,
        ORIGINS.FEEDPARSER: self.postprocess_feedparser_data,
        ORIGINS.TWITTER: self.postprocess_twitter_data,
    }

    meth = methods_table.get(self.origin, None)

    if meth is None:
        LOGGER.warning(u'%s %s: no method to post-process origin type %s.',
                       self_name, self_id, self.origin)
        return

    try:
        meth(force=force, commit=commit)

    except OriginalDataIncompatibleException:
        pass

    except OriginalDataStopProcessingException:
        pass

    except OriginalDataReprocessException:
        if first_run:
            self.postprocess_original_data(force=force, commit=commit,
                                           first_run=False)
        else:
            # This is a programmer's bug.
            raise RuntimeError(u'Running postprocess_original_data() should '
                               u'not happen twice automatically.')
    except:
        LOGGER.exception(u'%s %s: cxception while post-processing %s '
                         u'original data', self_name, self_id, self.origin)
    else:
        LOGGER.info(u'%s %s: post-processed %s original data.',
                    self_name, self_id, self.origin)


def BaseItem_postprocess_guess_original_data_method(self, force=False,
                                                    commit=True):

    need_save  = False
    self_name  = self._meta.verbose_name
    self_id    = self.id
    old_origin = self.origin

    try:
        original_data = self.original_data

    except:
        LOGGER.warning(u'%s %s: created original data on the fly.',
                       self_name, self_id)
        original_data = OriginalData(item=self)
        original_data.save()
        return

    if self.original_data.feedparser:
        self.origin = ORIGINS.FEEDPARSER
        need_save   = True

    elif self.original_data.google_reader:
        self.origin = ORIGINS.GOOGLE_READER
        need_save   = True

    elif self.original_data.twitter:
        self.origin = ORIGINS.TWITTER
        need_save   = True

    if need_save:
        if commit:
            self.save()

        if old_origin is None:
            LOGGER.warning(u'%s %s: discovered origin type %s, none before.',
                           self_name, self_id, self.origin)

        else:
            LOGGER.warning(u'%s %s: switched origin from %s to %s.',
                           self_name, self_id, old_origin, self.origin)

        raise OriginalDataReprocessException()


def BaseItem_postprocess_feedparser_data_method(self, force=False,
                                                commit=True):
    """ XXX: should disappear when feedparser_data is useless. """

    if self.original_data.feedparser_processed and not force:
        LOGGER.info('feedparser data already post-processed.')
        raise OriginalDataStopProcessingException

    fpod = self.original_data.feedparser_hydrated

    if fpod:

        if self.date_published is None:
            self.date_published = datetime_from_feedparser_entry(fpod)

        if self.tags == [] and 'tags' in fpod:
            tags = list(
                Tag.get_tags_set((
                    t['term']
                    # Sometimes, t['term'] can be None.
                    # http://dev.1flow.net/webapps/1flow/group/4082/
                    for t in fpod['tags'] if t['term'] is not None),
                    origin=self))

            self.update_tags(tags, initial=True, need_reload=False)

        if self.authors.count() == 0:
            Author.get_authors_from_feedparser_article(fpod,
                                                       set_to_article=self)

        if self.language is None:
            language = fpod.get('summary_detail', {}).get('language', None)

            if language is None:
                language = fpod.get('title_detail', {}).get(
                    'language', None)

            if language is not None:
                try:
                    self.language = Language.get_by_code(language)
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
    raise OriginalDataStopProcessingException


def BaseItem_postprocess_twitter_data_method(self, force=True, commit=True):
    """ Post-process the original tweet to make our tweet richer. """

    self_name = self._meta.verbose_name
    self_id = self.id

    if not isinstance(self, Tweet):

        # In case a double origin is found (eg. Twitter then RSS), this
        # call will raise OriginalDataReprocessException(), and the
        # feedparser data will be processed. See
        # RssAtomFeed.create_article_from_feedparser() for details.
        self.postprocess_guess_original_data()

        # In case the OriginalDataReprocessException() is not raised, we
        # have to stop here. We are a web article coming from a Tweet, we
        # have no original data anyway, nothing to process.
        LOGGER.warning(u'Not post-processing twitter original data of '
                       u'non-tweet %s %s.', self_name, self_id)
        raise OriginalDataIncompatibleException

    if self.original_data.twitter_processed and not force:
        LOGGER.info('Twitter data already post-processed.')
        raise OriginalDataStopProcessingException

    json_tweet = self.original_data.twitter_hydrated

    if json_tweet:

        LOGGER.debug(u'%s %s: post-processing Twitter data…',
                     self_name, self_id)

        language = Language.get_by_code(json_tweet['lang'])

        if language:
            self.language = language

        try:
            date_published = twitter_datestring_to_datetime_utc(
                json_tweet['created_at'])

        except:
            LOGGER.exception(u'Could not get tweet #%s date', self.tweet_id)

        else:
            self.date_published = date_published

        self.fetch_entities(json_tweet['entities'], commit=False)

        # WTF: putting this line after the "if tags:" doesn't do the job!
        self.save()

        if self.authors.count() == 0:
            author = Author.get_author_from_twitter_user(json_tweet['user'])

            if author:
                self.authors.add(author)

        tags = Tag.get_tags_set(
            [x['text'] for x in json_tweet['entities']['hashtags']],
            origin=self)

        if tags:
            self.tags.add(*tags)

    else:
        LOGGER.warning(u'%s %s: %s original data is empty!',
                       self_name, self_id, self.origin)

    self.original_data.twitter_processed = True
    self.original_data.save()


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
BaseItem.postprocess_twitter_data  = \
    BaseItem_postprocess_twitter_data_method


# HEADS UP: we need to register against BaseItem, because OriginalData
#           cannot .objects.get() an Article in register_task_method().
register_task_method(BaseItem, BaseItem.postprocess_original_data,
                     globals(), queue=u'background')
