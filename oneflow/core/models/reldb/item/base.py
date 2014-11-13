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

# from humanize.time import naturaldelta
# from humanize.i18n import django_language

# from django.conf import settings
from django.db import models, IntegrityError
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from polymorphic import (
    PolymorphicQuerySet,
    PolymorphicManager,
    PolymorphicModel,
)

# from oneflow.base.utils.dateutils import now
# from oneflow.base.utils import register_task_method

from ..common import (
    DjangoUser as User,
    ORIGINS,
)

from ..language import AbstractLanguageAwareModel
from ..duplicate import AbstractDuplicateAwareModel
from ..tag import AbstractTaggedModel
from ..author import Author
# from ..source import Source


LOGGER = logging.getLogger(__name__)


__all__ = [
    'BaseItem',

    # 'baseitem_pre_save',
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

        LOGGER.info(u'Item %s replaced by %s everywhere %s.', duplicate, self,
                    u'successfully' if all_went_ok else u'with some error(s).')

        return all_went_ok

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
