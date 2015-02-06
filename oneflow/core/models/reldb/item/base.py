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

# from statsd import statsd
# from constance import config

from humanize.time import naturaldelta
from humanize.i18n import django_language

# from django.conf import settings
from django.db import models, IntegrityError
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify
from django.contrib.contenttypes import generic

from polymorphic import (
    PolymorphicQuerySet,
    PolymorphicManager,
    PolymorphicModel,
)

from oneflow.base.utils.dateutils import now, timedelta
from oneflow.base.utils import register_task_method

from ..common import (
    DjangoUser as User,
    ORIGINS,
)

from ..language import AbstractLanguageAwareModel
from ..duplicate import AbstractDuplicateAwareModel
from ..tag import AbstractTaggedModel
from ..author import Author
from ..processor import ProcessingError, run_processing_chains
# from ..source import Source


LOGGER = logging.getLogger(__name__)


__all__ = [
    'BaseItem',

    # 'baseitem_pre_save',
    # Task methods will be added by register_task_method()
]


# ———————————————————————————————————————————————————————————————————— Managers


class BaseItemQuerySet(PolymorphicQuerySet):

    """ Item based queryset.

    .. note:: this query set will be patched by subclasses.
    """

    def restricted(self):
        return self.filter(is_restricted=True)

    def unrestricted(self):
        return self.filter(is_restricted=False)

    def original(self):
        return self.filter(origin=None)

    def master(self):
        return self.filter(duplicate_of_id=None)

    def duplicate(self):
        return self.exclude(duplicate_of_id=None)

    def created_previous_hour(self):
        """ Return items created between 61 and 120 minutes inclusive. """

        one_hour_delta = timedelta(seconds=3600)
        one_hour_before = now() - one_hour_delta
        two_hours_before = one_hour_before - one_hour_delta

        return self.filter(date_created__lte=one_hour_before,
                           date_created__gte=two_hours_before)

    def created_previous_day(self):
        """ Return items created between 25 and 48 hours inclusive. """

        one_day_delta = timedelta(days=1)
        one_day_before = now() - one_day_delta
        two_days_before = one_day_before - one_day_delta

        return self.filter(date_created__lte=one_day_before,
                           date_created__gte=two_days_before)

    def created_previous_week(self):
        """ Return items created between 8 and 14 days inclusive. """

        one_week_delta = timedelta(days=7)
        one_week_before = now() - one_week_delta
        two_weeks_before = one_week_before - one_week_delta

        return self.filter(date_created__lte=one_week_before,
                           date_created__gte=two_weeks_before)

    def created_previous_month(self):
        """ Return items created between 32 and 62 days inclusive. """

        one_month_delta = timedelta(days=31)
        one_month_before = now() - one_month_delta
        two_months_before = one_month_before - one_month_delta

        return self.filter(date_created__lte=one_month_before,
                           date_created__gte=two_months_before)

    def older_than_one_day(self):
        """ Return items created more than 24 hours ago. """

        one_day_delta = timedelta(days=1)
        one_day_before = now() - one_day_delta

        return self.filter(date_created__lte=one_day_before)

    def older_than_one_week(self):
        """ Return items created more than 7 days ago. """

        one_week_delta = timedelta(days=7)
        one_week_before = now() - one_week_delta

        return self.filter(date_created__lte=one_week_before)

    def older_than_two_weeks(self):
        """ Return items created more than 14 days ago. """

        two_week_delta = timedelta(days=14)
        two_weeks_before = now() - two_week_delta

        return self.filter(date_created__lte=two_weeks_before)

    def older_than_one_month(self):
        """ Return items created more than 31 days ago. """

        one_month_delta = timedelta(days=31)
        one_month_before = now() - one_month_delta

        return self.filter(date_created__lte=one_month_before)

    def older_than_delta(self, custom_timedelta):
        """ Return items created more than :param:`delta` ago.

        :param delta: a python :class:`~datetime.timedelta` object.
        """

        custom_delta_before = now() - custom_timedelta

        return self.filter(date_created__lt=custom_delta_before)


class BaseItemManager(PolymorphicManager):

    """ A manager that adds some things. """

    use_for_related_fields = True
    queryset_class = BaseItemQuerySet


# ——————————————————————————————————————————————————————————————————————— Model


class BaseItem(PolymorphicModel,
               AbstractDuplicateAwareModel,
               AbstractLanguageAwareModel,
               AbstractTaggedModel):

    """ The base item in the 1flow database.


    .. todo::
        title → name
        orphaned → is_orphaned
        origin_type → origin
        date_added → date_created

    """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Base item')
        verbose_name_plural = _(u'Base items')
        get_latest_by = 'date_published'

    objects = BaseItemManager()

    name = models.CharField(max_length=1024, verbose_name=_(u'Name'))
    slug = models.CharField(max_length=1024, null=True, blank=True)
    user = models.ForeignKey(User, null=True, blank=True,
                             verbose_name=_(u'Creator'))

    # not yet.
    # short_url  = URLField(unique=True, verbose_name=_(u'1flow URL'))

    is_restricted = models.BooleanField(
        verbose_name=_(u'restricted'),
        help_text=_(u'This article comes from a paid paid subscription '
                    u'and cannot be shared like others inside the platform.'),
        default=False, blank=True)

    date_created = models.DateTimeField(
        auto_now_add=True, db_index=True,
        verbose_name=_(u'Date added'),
        help_text=_(u'When the article was added to the 1flow database.'))

    date_updated = models.DateTimeField(
        auto_now=True, verbose_name=_(u'Date updated'),
        help_text=_(u'When the article was updated.'))

    date_published = models.DateTimeField(
        verbose_name=_(u'date published'),
        null=True, blank=True, db_index=True,
        help_text=_(u"When the item was put online."))

    authors = models.ManyToManyField(
        Author, null=True, blank=True,
        verbose_name=_(u'Authors'), related_name='authored_items')

    default_rating = models.FloatField(
        default=0.0, blank=True,
        verbose_name=_(u'default rating'),
        help_text=_(u'Rating used as a base when a user has not already '
                    u'rated the content.'))

    text_direction = models.CharField(verbose_name=_(u'Text direction'),
                                      choices=((u'ltr', _(u'Left-to-Right')),
                                               (u'rtl', _(u'Right-to-Left'))),
                                      default=u'ltr', max_length=3,
                                      db_index=True)

    processing_errors = generic.GenericRelation(
        ProcessingError,
        content_type_field='instance_type',
        object_id_field='instance_id')

    # ———————————————————————————————————————————————————————————————— Contents
    #
    # Articles have an excerpt and a content.
    #
    # Bookmarks have just an URL and some images.
    #
    # Tweets and similar objects have an URL and a small content. They are
    # similar to articles, with less different things to do on content, given
    # the type of what they are.
    #
    # Documents have files, stored outside of the database.
    #
    # Thus, BaseItem has no content per se, but only an excerpt.
    #
    # ———————————————————————————————————————————————————————————— End contents

    # A snap / a serie of snaps references the original article.
    # An article references its source (origin blog / newspaper…)
    sources = models.ManyToManyField('self', blank=True, null=True,
                                     verbose_name=_(u'Sources'))

    # For items which don't have any source, they should have an external
    # origin and most probably an original_data.
    origin = models.IntegerField(
        verbose_name=_(u'Origin'),
        null=True, blank=True,
        choices=ORIGINS.get_choices(),
        help_text=_(u'Origin of article (RSS/Atom, web import, twitter…). '
                    u'Can be None if item has a source (=internal origin).'))

    def __unicode__(self):
        return _(u'{0} (#{1}){2}').format(
            self.name[:40] + (self.name[40:] and u'…'), self.id,
            u' by {0}'.format(self.user.username) if self.user else u'')

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def date_published_delta(self):

        with django_language():
            return _(u'{0} ago').format(naturaldelta(self.date_published))

    @property
    def a_feed(self):
        """ Get any of the item's feeds. None if it hasn't any.

        (but that's highly unprobable).
        """

        try:
            return self.feeds.all()[0]

        except IndexError:
            return None

    @property
    def get_source(self):

        return self.sources.all() or self.feeds.all() or _(u'Unknown source')

    @property
    def get_source_unicode(self):

        source = self.get_source

        if source.__class__ in (unicode, str):
            return source

        sources_count = source.count()

        if sources_count > 2:
            return _(u'Multiple sources ({0} feeds)').format(sources_count)

        return u' / '.join(x.name for x in source)

    @property
    def is_good(self):
        """ Return ``True`` if the current article
            is ready to be seen by final users. """

        if self.duplicate_of:
            return False

        return True

    # ————————————————————————————————————————————————————————————————— Methods

    def get_processing_chain(self):
        """ Return no processor chain.

        BaseItem is too generic and too empty to have a processor chain ?

        This method should be overriden by inheriting classes.
        """

        return None

    def run_processing_chain(self, verbose=True, force=False, commit=True):
        """ Run processors for the content item. """

        processing_chain = self.get_processing_chain()

        if processing_chain is None:
            run_processing_chains(self, verbose=verbose,
                                  force=force, commit=commit)

        else:
            processing_chain.run(self, verbose=verbose,
                                 force=force, commit=commit)

    def reset(self, force=False, commit=True):
        """ See :meth:`Article.reset`() for explanations. """

        if not force:
            LOGGER.warning(u'Cannot reset base fields '
                           u'without `force` argument.')
            return

        if self.processing_errors.exists():
            count = self.processing_errors.count()
            self.processing_errors.clear()
            LOGGER.info(u'Cleared %s processing errors…', count)

        return

    def update_tags(self, tags, initial=False):

        if initial:
            self.tags.clear()

        self.tags.add(*tags)

        for read in self.reads:
            if initial:
                read.tags.clear()

            read.tags.add(*tags)

    def replace_duplicate(self, duplicate, force=False):
        """ register :param:`duplicate` as a duplicate of myself.

        redirect/modify all reads and feeds links to me, keeping all
        attributes as they are.

        .. warning:: this method is called INSIDE a celery
            task (but it is not one by itself).
        """

        all_went_ok = True

        try:
            self.feeds.add(*duplicate.feeds.all())

        except:
            all_went_ok = False
            # We have to continue to replace reads,
            # and reload() at the end of the method.
            LOGGER.exception(u'Could not update %s feeds with the ones '
                             u'from %s!', self, duplicate)

        for read in duplicate.reads.all():
            read.item = self

            try:
                read.save()

            except IntegrityError:
                # The user has already a Read with the master item.
                # The one we are trying to save() would be the same.
                # Just delete it.
                read.delete()

            except:
                all_went_ok = False
                LOGGER.exception(u'Could not replace current item in '
                                 u'read %s by %s!', read, self)

        for tweet in duplicate.tweets.all():
            try:
                tweet.entities.add(self)
                tweet.entities.remove(duplicate)

            except:
                all_went_ok = False
                LOGGER.exception(u'Could not replace current item in '
                                 u'read %s by %s!', read, self)

        LOGGER.info(u'Item #%s replaced by #%s everywhere %s.',
                    duplicate.id, self.id,
                    u'successfully' if all_went_ok else u'with some error(s).')

        return all_went_ok

    def create_reads(self, feeds=None):
        """ Create an article reads for all of its feeds.

        .. note:: this method is run via a celery task.
        """

        # Even if the article wasn't created, we need to create reads.
        # In the case of a mutualized article, it will be fetched only
        # once, but all subscribers of all feeds must be connected to
        # it to be able to read it.

        if self.duplicate_of_id:
            LOGGER.warning(u'Not creating reads for duplicate %s #%s',
                           self._meta.model.__name__, self.id)
            return

        if feeds is None:
            feeds = self.feeds.all()

        for feed in feeds:
            for subscription in feed.subscriptions.all():
                subscription.create_read(self)

    def activate_reads(self, force=False, verbose=False, extended_check=False):

        if self.is_good or force:

            bad_reads = self.bad_reads.all()

            if verbose:
                LOGGER.info(u'Article %s activating %s bad reads…',
                            self, bad_reads.count())

            for read in bad_reads:
                try:
                    if extended_check:
                        read.check_subscriptions()

                    # We 'force' to avoid the reverse test in Read.
                    # We already know the article is OK.
                    read.activate(force=True)

                except:
                    # During a check, we cannot activate all reads at once
                    # if some of them have dangling subscriptions references.
                    # But this is harmless, because they will be corrected
                    # later in the global check.
                    LOGGER.exception(u'Activation failed for Read #%s from '
                                     u'Article #%s.', read.id, self.id)

        else:
            if verbose:
                LOGGER.warning(u'Will not activate reads of bad article %s',
                               self)


# ——————————————————————————————————————————————————————————————————————— Tasks


register_task_method(BaseItem, BaseItem.create_reads,
                     globals(), queue=u'create')
