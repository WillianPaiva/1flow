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

import json
import logging

# from statsd import statsd
from random import randrange
from json_field import JSONField
from dateutil import parser as date_parser

# from django.conf import settings
from django.core.validators import URLValidator
from django.db import models
from django.db.models.signals import post_save
# from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.contrib.messages import constants

from async_messages import message_user

from sparks.django.utils import NamedTupleChoices

from oneflow.base.utils import register_task_method
from oneflow.base.utils.dateutils import now, timedelta, naturaldelta

from history import HistoryEntry

from ..common import ORIGINS, CONTENT_TYPES

from . import (
    Article, Read,
    create_item_from_url,
    create_feeds_from_url,
    subscribe_user_to_feed,
    FeedIsHtmlPageException,
)


LOGGER = logging.getLogger(__name__)


__all__ = [
    'UserImport',
    'IMPORT_STATUS',
]


IMPORT_STATUS = NamedTupleChoices(
    'IMPORT_STATUS',

    ('NEW', 0, _(u'new')),

    # Used to avoid starting the task at creation.
    ('MANUAL', 1, _(u'manual')),

    ('RUNNING', 2, _(u'running')),
    ('FINISHED', 3, _(u'finished')),
    ('FAILED', 4, _(u'failed')),
    ('RETRY', 5, _('Retried')),
)


class UserImport(HistoryEntry):

    """ Keep trace of user imports, and run them in background tasks. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'User import')
        verbose_name_plural = _(u'User imports')

    date_started = models.DateTimeField(null=True, blank=True,
                                        verbose_name=_(u'date started'))
    date_finished = models.DateTimeField(null=True, blank=True,
                                         verbose_name=_(u'date finished'))
    status = models.IntegerField(verbose_name=_(u'Status'),
                                 choices=IMPORT_STATUS.get_choices(),
                                 default=IMPORT_STATUS.NEW, blank=True)

    urls = models.TextField(verbose_name=_(u'Web addresses'))
    lines = models.IntegerField(verbose_name=_(u'lines'), default=0)
    results = JSONField(default=dict, blank=True)

    def __unicode__(self):
        """ Unicode, pep257. """

        return _(u'Import #{0} for user {1}').format(self.id, self.user)

    # ——————————————————————————————————————————————————————————————————— Utils

    @property
    def running_old(self):
        """ An import running for too long is probably crashed.

        But we didn't notice it, or celery crashed. Whatever.
        """

        return self.status == IMPORT_STATUS.RUNNING \
            and self.date_started < (now() - timedelta(seconds=21600))

    @property
    def count(self):
        """ Count how many lines we have in this import. """

        return len(self.urls.splitlines())

    @property
    def importers(self):
        """ Return a generator on one-type importers.

        These importers are methods whose name
        starts with ``guess_and_import_``.
        """

        for attr_name in dir(self):
            if attr_name.startswith('guess_and_import_'):
                yield getattr(self, attr_name)

    def validate_url(self, url):
        """ Validate an URL. """

        url = url.strip()

        if not url:
            return False

        try:
            self._import_validator_(url)

        except Exception as e:
            self._import_failed_.append((url, u', '.join(e.messages)))
            return False

        else:
            if url in self._import_to_create_:
                return False

            # Avoid stupidity.
            if u'1flow.io/' in url or u'1flow.net/' in url:
                try:
                    #
                    # HACK: if we try to import an article from another
                    # user's page. This is quick and dirty, but sufficient
                    # until we have an auto-clone feature.
                    #

                    # extract a potential read_id from
                    # http://1flow.io/fr/lire/52c2beba84cc1762a69c4c2e/
                    # get it from the end, because matching any reverse_lazy()
                    # is too complicated, given the lang of the 2 users.
                    read_id = url[-26:].split('/', 1)[1].replace('/', '')

                except:
                    return False

                try:
                    Read.objects.get(id=read_id)

                except:
                    return False

                else:
                    return True

            self._import_to_create_.add(url)

            return True

    # ———————————————————————————————————————————— One-type importers/detectors

    def guess_and_import_readability(self):
        """ Guess if our content is a readability file, then import it. """

        try:
            readability_json = json.loads(self.urls)

        except:
            return False

        try:
            first_object = readability_json[0]

        except:
            return False

        for attr_name in ("article__title", "article__excerpt",
                          "article__url", "date_added",
                          "favorite", "date_favorited",
                          "archive", "date_archived"):
            if attr_name not in first_object:
                return False

        message_user(self.user,
                     _(u'Readability JSON export format detected.'),
                     constants.INFO)

        for readability_object in readability_json:

            url = readability_object['article__url']

            if self.validate_url(url):
                article = self.import_from_one_url(
                    url,
                    origin=ORIGINS.READABILITY
                )

                if article is None:
                    # article was not created, we
                    # already have it in the database.
                    article = Article.objects.get(url=url)

                #
                # Now comes the readability-specific part of the import,
                # eg. get back user meta-data as much as possible in 1flow.
                #

                article_needs_save = False

                if readability_object['article__title']:
                    article.name      = readability_object['article__title']
                    article_needs_save = True

                if readability_object['article__excerpt']:
                    article.excerpt    = readability_object['article__excerpt']
                    article_needs_save = True

                if article_needs_save:
                    article.save()

                read = article.reads.get(
                    subscriptions=self.user.user_subscriptions.imported_items)

                # About parsing dates:
                # http://stackoverflow.com/q/127803/654755
                # http://stackoverflow.com/a/18150817/654755

                read_needs_save = False

                date_added = readability_object['date_added']

                if date_added:
                    # We try to keep the history of date when the
                    # user added this article to readability.
                    try:
                        read.date_created = date_parser.parse(date_added)

                    except:
                        LOGGER.exception(u'Parsing creation date "%s" for '
                                         u'read #%s failed.', date_added,
                                         read.id)

                    else:
                        read_needs_save = True

                if readability_object['favorite']:
                    read.is_starred = True
                    read_needs_save = True

                    date_favorited = readability_object['date_favorited']

                    if date_favorited:
                        try:
                            read.date_starred = date_parser.parse(
                                date_favorited)
                        except:
                            LOGGER.exception(u'Parsing favorited date "%s" '
                                             u'for read #%s failed.',
                                             date_favorited, read.id)

                if read_needs_save:
                    read.save()

        return True

    def guess_and_import_wallabag(self):
        """ Try to import a JSON export file from wallabag. """

        try:
            wallabag_json = json.loads(self.urls)

        except:
            return False

        try:
            first_object = wallabag_json[0]

        except:
            return False

        for attr_name in (
            "0", "1", "2", "3", "4", "5", "6",
            "content", "id", "is_fav", "is_read",
            "title", "url", "user_id",
        ):
            if attr_name not in first_object:
                return False

        message_user(self.user,
                     _(u'Wallabag JSON export format detected.'),
                     constants.INFO)

        for wallabag_object in wallabag_json:

            url = wallabag_object['url']

            if self.validate_url(url):
                article = self.import_from_one_url(
                    url,
                    origin=ORIGINS.WALLABAG
                )

                if article is None:
                    # article was not created, we
                    # already have it in the database.
                    article = Article.objects.get(url=url)

                # Now comes the wallabag-specific part of the import,
                # eg. get back user meta-data as much as possible in 1flow.

                article_needs_save = False
                article_needs_convert = False

                title = wallabag_object.get('title', None)

                if title:
                    article.name       = title
                    article_needs_save = True

                content = wallabag_object['content']

                if content:
                    article.content       = content
                    article.content_type  = CONTENT_TYPES.HTML
                    article_needs_save    = True
                    article_needs_convert = True

                if article_needs_save:
                    article.save()

                if article_needs_convert:
                    article.convert_to_markdown()

                read = article.reads.get(
                    subscriptions=self.user.user_subscriptions.imported_items)

                # About parsing dates:
                # http://stackoverflow.com/q/127803/654755
                # http://stackoverflow.com/a/18150817/654755

                read_needs_save = False

                if wallabag_object.get('is_fav', False):
                    read.is_starred = True
                    read_needs_save = True

                    # This information is not in wallabag.
                    read.date_starred = now()

                if wallabag_object.get('is_read', False):
                    read.is_read = True
                    read_needs_save = True

                    # This information is not in wallabag.
                    read.date_read = now()

                if read_needs_save:
                    read.save()

        return True

    # ———————————————————————————————————————————————— 1flow internal importers

    def import_from_one_url(self, url, origin=None):
        """ Guess if an URL is a feed or an article and import it. """

        # —————————————————————————————————————— Try to create an RSS/Atom Feed

        feeds = None

        try:
            feeds = create_feeds_from_url(url)

        except FeedIsHtmlPageException:
            # This is expected if we are importing web pages URLs.
            pass

        except Exception as e:
            LOGGER.exception(u'Exception occured while trying to create '
                             u'feed(s) from %s', url)

        if feeds:
            imported_item_was_a_feed_url = False

            for feed, created in feeds:
                if feed.url == url:
                    imported_item_was_a_feed_url = True
                    break

            if imported_item_was_a_feed_url:
                self._import_created_['feeds'].append(url)

                # Subscribe the user to the feed, and don't
                # try to import an article from the URL.

                for feed, created in feeds:

                    subscribe_user_to_feed(user=self.user,
                                           feed=feed,
                                           background=True)

                    if created:
                        message_user(self.user,
                                     _(u'Successfully subscribed to new feed '
                                       u'“{0}”. Thank you!').format(feed.name),
                                     constants.INFO)
                    else:
                        message_user(self.user,
                                     _(u'Successfully subscribed to feed '
                                       u'“{0}”.').format(feed.name),
                                     constants.INFO)

                return None

            else:
                self._import_created_['discovered'] = [
                    feed.url for feed, created in feeds if created
                ]

        # ———————————————————————————————————————————— Try to create an article

        article = None

        try:
            article, created = create_item_from_url(
                url,
                feeds=[self.user.user_feeds.imported_items],
                origin=origin
            )

            # create_item_from_url() will run subscription.create_read()
            # for all feeds, thus the read is assumed to be ready now.
            read = Read.objects.get(item=article, user=self.user)
            read.mark_archived()

        except Exception as e:
            LOGGER.exception(u'Could not create article from URL %s', url)
            self._import_failed_.append((url, unicode(e)))

        else:
            self._import_created_['articles'].append(url)

            message_user(self.user,
                         _(u'Successfully imported article '
                           u'“{0}”.').format(article.name),
                         constants.INFO)

        return article

    # ———————————————————————————————————————————————— All-in-one import runner

    def run(self):
        """ Run the import. """

        #
        # NOTE: we don't care if the import was already running, finished,
        #       whatever. This class is able to recover and re-run itself
        #       over and over without doing bad thing in the database.
        #

        is_retrying = self.status == IMPORT_STATUS.RETRY

        self.status = IMPORT_STATUS.RUNNING
        self.date_started = now()
        self.save()

        try:
            return self.run_internal()

        except:
            LOGGER.exception(u'User import %s failed')

            if is_retrying:
                message_user(self.user,
                             _(u'Your import #{0} failed to run after a '
                               u'retry. Please review it before relaunching '
                               u'it manually again.').format(self.id),
                             constants.ERROR)

                self.status = IMPORT_STATUS.FAILED

            else:
                countdown = randrange(1800, 3600)
                delta_cd = naturaldelta(timedelta(seconds=countdown))

                message_user(self.user,
                             _(u'Your import #{0} failed to run. If will '
                               u'be automatically retried in {1}').format(
                                 self.id, delta_cd),
                             constants.WARNING)

                globals()['userimport_run_task'].apply_async(
                    (self.id, ), countdown=countdown)

                self.status = IMPORT_STATUS.RETRY

            self.save()

    def run_internal(self):
        """ Import dirty work. """

        self._import_validator_ = URLValidator()
        self._import_to_create_ = set()
        self._import_created_   = {
            'feeds': [],
            'articles': []
        }
        self._import_failed_ = []

        all_in_one = False

        for importer in self.importers:
            if importer():
                all_in_one = True
                break

        if not all_in_one:
            urls = self.urls.splitlines()

            for url in urls:
                self.validate_url(url)

            for url in self._import_to_create_:
                self.import_from_one_url(url)

        self.results = {
            'created': self._import_created_,
            'failed': self._import_failed_,
        }

        if self._import_created_['articles'] or self._import_created_['feeds']:
            self.status = IMPORT_STATUS.FINISHED

        elif self._import_failed_:
            self.status = IMPORT_STATUS.FAILED

        self.date_finished = now()
        self.save()

# ———————————————————————————————————————————————————————————— Methods as tasks


register_task_method(UserImport, UserImport.run,
                     globals(), queue=u'background')

# ————————————————————————————————————————————————————————————————————— Signals


def userimport_post_save(instance, **kwargs):

    if kwargs.get('created', False):
        # HEADS UP: this task is declared by
        # the register_task_method call below.
        userimport_run_task.delay(instance.id)  # NOQA

    elif instance.status == IMPORT_STATUS.NEW:
        # relaunch the importer task.

        # HEADS UP: this task is declared by
        # the register_task_method call below.
        userimport_run_task.delay(instance.id)  # NOQA

post_save.connect(userimport_post_save, sender=UserImport)
