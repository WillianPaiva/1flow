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

# from celery import chain as tasks_chain

# from humanize.time import naturaldelta
# from humanize.i18n import django_language

# from django.conf import settings
from django.db import models, IntegrityError
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from polymorphic import PolymorphicModel

# from sparks.foundations.classes import SimpleObject
# from sparks.django.models import DiffMixin

# from oneflow.base.utils.http import clean_url
# from oneflow.base.utils.dateutils import now
# from oneflow.base.utils import register_task_method

from ..common import (
    DjangoUser as User,
    ORIGINS,
)

from ..tag import SimpleTag
from ..duplicate import AbstractDuplicateAwareModel
from ..author import Author
# from ..source import Source


LOGGER = logging.getLogger(__name__)


__all__ = [
    'BaseItem',

    # 'baseitem_pre_save',
]


# ——————————————————————————————————————————————————————————————————— end ghost
#

class BaseItem(PolymorphicModel,
               AbstractDuplicateAwareModel,
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
        verbose_name = _(u'Base items')

    name = models.CharField(max_length=256, verbose_name=_(u'Name'))
    slug = models.CharField(max_length=256, null=True, blank=True)
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
        auto_now_add=True, verbose_name=_(u'Date added'),
        help_text=_(u'When the article was added to the 1flow database.'))

    date_updated = models.DateTimeField(
        auto_now=True, verbose_name=_(u'Date updated'),
        help_text=_(u'When the article was updated.'))

    authors = models.ManyToManyField(
        Author, null=True, blank=True,
        verbose_name=_(u'Authors'), related_name='authored_items')

    tags = models.ManyToManyField(
        SimpleTag, verbose_name=_(u'Tags'),
        blank=True, null=True, related_name='items',
        help_text=_(u'Default tags that will be applied to the READ objects.'))

    default_rating = models.FloatField(
        default=0.0, blank=True,
        verbose_name=_(u'default rating'),
        help_text=_(u'Rating used as a base when a user has not already '
                    u'rated the content.'))

    language = models.CharField(verbose_name=_(u'Article language'),
                                max_length=5,
                                help_text=_(u'2 letters or 5 characters '
                                            u'language code (eg “en”, '
                                            u'“fr-FR”…).'))
    text_direction = models.CharField(verbose_name=_(u'Text direction'),
                                      choices=((u'ltr', _(u'Left-to-Right')),
                                               (u'rtl', _(u'Right-to-Left'))),
                                      default=u'ltr', max_length=3)

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

        try:
            self.feeds.add(*duplicate.feeds.all())

        except:
            # We have to continue to replace reads,
            # and reload() at the end of the method.
            LOGGER.exception(u'Could not update %s feeds with the ones '
                             u'from %s!', self, duplicate)

        for read in duplicate.reads.all():
            read.item = self

            try:
                read.save()

            except IntegrityError:
                LOGGER.exception(u'Read %s already has master item %s '
                                 u'instead of duplicate %s?!?',
                                 read, self, duplicate)
                # Already registered, simply delete the read.
                read.delete()

            except:
                LOGGER.exception(u'Could not replace current item in '
                                 u'read %s by %s!', read, self)

        LOGGER.info(u'Item %s replaced by %s everywhere.', duplicate, self)

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


# —————————————————————————————————————————————————————— external bound methods
#                                            Defined here to avoid import loops


def SimpleTag_replace_duplicate_in_items_method(self, duplicate, force=False):
    """ Replace a duplicate of a Tag in all items/reads having it set. """

    #
    # TODO: update search engine indexes…
    #

    for item in duplicate.items.all():
        item.tags.remove(duplicate)
        item.tags.add(self)

    for read in duplicate.reads.all():
        read.tags.remove(duplicate)
        read.tags.add(self)


SimpleTag.replace_duplicate_in_items = \
    SimpleTag_replace_duplicate_in_items_method
