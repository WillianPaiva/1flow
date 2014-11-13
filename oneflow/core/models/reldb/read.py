
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

import sys
import logging
import operator

from statsd import statsd

from django.db import models
from django.db.models.signals import pre_delete, post_save  # , pre_save
from django.db.models.query import QuerySet
# from django.conf import settings
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from oneflow.base.utils.dateutils import timedelta, naturaldelta, datetime

from sparks.django.utils import NamedTupleChoices

from common import (
    DjangoUser as User,
    READ_STATUS_DATA,
    WATCH_ATTRIBUTES_FIELDS_NAMES,
)

from folder import Folder

# Avoid import loop.
# from subscription import Subscription, generic_check_subscriptions_method

from tag import AbstractTaggedModel, SimpleTag as Tag
from item.base import BaseItem

LOGGER = logging.getLogger(__name__)

MIGRATION_DATETIME = datetime(2014, 11, 1)


__all__ = [
    'Read',
    'ReadManager',
    'ReadQuerySet',
    'BOOKMARK_TYPES',
]


BOOKMARK_TYPES = NamedTupleChoices(
    'BOOKMARK_TYPES',
    ('UNDEFINED', u'U', _(u'Undefined')),
    ('AFTERNOON', u'A', _(u'This afternoon')),
    ('WEEK_END', u'W', _(u'This week-end')),

    # The second char will be used for user defined bookmark types.
    ('CUSTOM', u'C', _(u'Custom (user defined)')),
)

BOOKMARK_TYPE_DEFAULT = u'U'


# ———————————————————————————————————————————————————————————————————— Managers


class ReadQuerySet(QuerySet):

    """ QuerySet that helps reads filtering. """

    def good(self):
        return self.filter(is_good=True)

    def bad(self):
        return self.filter(is_good=False)

    def read(self):
        return self.filter(is_read=True)

    def unread(self):
        return self.filter(is_read=False)

    def auto_read(self):
        return self.filter(is_auto_read=True)

    def archived(self):
        return self.filter(is_archived=True)

    def bookmarked(self):
        return self.filter(is_bookmarked=True)

    def starred(self):
        return self.filter(is_starred=True)


class ReadManager(models.Manager):

    """ A manager to wrap our query set.

    .. note:: this one should eventually vanish in Django 1.7.
    """

    use_for_related_fields = True

    def get_queryset(self):
        return ReadQuerySet(self.model, using=self._db)

    # VANISH in Django 1.7 → use `ReadQS.as_manager()`

    def good(self):
        return self.get_queryset().filter(is_good=True)

    def bad(self):
        return self.get_queryset().filter(is_good=False)


class Read(AbstractTaggedModel):

    """ Link a user to any item. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Read')
        verbose_name_plural = _(u'Reads')
        unique_together = ('user', 'item', )

    objects = ReadManager()

    item = models.ForeignKey(BaseItem, related_name='reads')
    user = models.ForeignKey(User, related_name='all_reads')

    senders = models.ManyToManyField(
        User, verbose_name=_(u'Senders'),
        related_name='reads_sent', null=True, blank=True,
        help_text=_(u'All the users that have shared the article with the '
                    u'current owner of this read.'))

    date_created = models.DateTimeField(auto_now_add=True,
                                        db_index=True, blank=True)

    is_good = models.BooleanField(
        verbose_name=_('good for use?'),
        help_text=_(u'The system has validated the underlying article, and '
                    u'the read can now be shown, used by its owner, and '
                    u'counted in statistics.'),
        default=False, blank=True, db_index=True)

    is_read = models.BooleanField(
        verbose_name=_(u'is read?'),
        help_text=_(u'The Owner has read the content or has manually '
                    u'marked it as such.'),
        default=False, db_index=True)
    date_read = models.DateTimeField(null=True, blank=True)

    is_auto_read = models.BooleanField(
        verbose_name=_(u'is automatically read?'),
        help_text=_(u'The system has automatically marked it as read, in '
                    u'respect of a system rule or a user preference.'),
        default=False, blank=True)
    date_auto_read = models.DateTimeField(null=True, blank=True)

    is_archived = models.BooleanField(
        verbose_name=_(u'is archived?'),
        help_text=_(u'The Owner has archived this read to explicitely '
                    u'keep it accessible.'),
        default=False, blank=True)
    date_archived = models.DateTimeField(null=True, blank=True)

    # NOTE: is_starred is a NullBoolean because we use True
    #       as "I like it" and False as "I don't like it",
    #       thus no default means null.
    is_starred = models.NullBooleanField(
        verbose_name=_(u'is starred?'),
        help_text=_(u'The owner has starred the content, signifying '
                    u'he/she loves it or that it is much of interest '
                    u'for him/her.'),
        null=True, blank=True, db_index=True)
    date_starred = models.DateTimeField(null=True, blank=True)

    is_bookmarked = models.BooleanField(
        verbose_name=_(u'is bookmarked?'),
        help_text=_(u'This content is marked to be read later. When, '
                    u'depends on the `.bookmark_type` attribute.'),
        default=False, blank=True, db_index=True)
    date_bookmarked = models.DateTimeField(null=True, blank=True)
    bookmark_type = models.CharField(
        verbose_name=_(u'Bookmark type'),
        max_length=2, default=u'U',
        choices=BOOKMARK_TYPES.get_choices())

    # —————————————————————————————————————————————————————— START make generic

    is_fact = models.BooleanField(
        help_text=_(u'Qualifies a time-dependant fact.'),
        default=False, blank=True)
    date_fact = models.DateTimeField(null=True, blank=True)

    is_quote = models.BooleanField(
        help_text=_(u'Qualifies someone’s words, thoughts or intentions.'),
        default=False, blank=True)
    date_quote = models.DateTimeField(null=True, blank=True)

    is_number = models.BooleanField(
        help_text=_(u'Qualifies explicitely quantized data.'),
        default=False, blank=True)
    date_number = models.DateTimeField(null=True, blank=True)

    is_analysis = models.BooleanField(
        help_text=_(u'Qualifies in-depth analysis, studies or research '
                    u'publications.'),
        default=False, blank=True)
    date_analysis = models.DateTimeField(null=True, blank=True)

    is_prospective = models.BooleanField(
        help_text=_(u'Qualifies things that want to watch, that will '
                    u'happen or not.'),
        default=False, blank=True)
    date_prospective = models.DateTimeField(null=True, blank=True)

    is_knowhow = models.BooleanField(
        help_text=_(u'Qualifies anything about How-to-do things '
                    u'and profession best-practices.'),
        default=False, blank=True)
    date_knowhow = models.DateTimeField(null=True, blank=True)

    is_rules = models.BooleanField(
        help_text=_(u'Qualifies anything about laws, governments/public '
                    u'regulations.'),
        default=False, blank=True)
    date_rules = models.DateTimeField(null=True, blank=True)

    is_knowledge = models.BooleanField(
        help_text=_(u'Qualifies anything that the owner wants to retain '
                    u'as a “must know”, whatever the context.'),
        default=False, blank=True)
    date_knowledge = models.DateTimeField(null=True, blank=True)
    knowledge_type = models.CharField(max_length=2, null=True, blank=True)

    is_fun = models.BooleanField(
        help_text=_(u'Qualifies anything that makes you laugh out loud.'),
        default=False, blank=True)
    date_fun = models.DateTimeField(null=True, blank=True)

    # ———————————————————————————————————————————————————————— END make generic

    # This will be set to Article.default_rating
    # until the user sets it manually.
    rating = models.FloatField(null=True, blank=True)

    # ————————————————————————————————————————————————————————— Temporary space
    #                                 things here will have a limited lifetime.
    #
    #
    #

    # At the time this is created, set_subscriptions() does the right thing.
    # Don't let new reads be checked more than once, the database is already
    # overloaded with post-processing and normal end-users related usage.
    check_set_subscriptions_131004_done = models.BooleanField(
        default=True)

    def check_set_subscriptions_131004(self):
        """ Fix a bug where reads had too much subscriptions. """

        subscriptions_to_keep = []

        for subscription in self.subscriptions.all():
            try:
                if subscription.user == self.user:
                    subscriptions_to_keep.append(subscription)
            except:
                sys.stderr.write(u'-')

        self.subscriptions.clear()

        if subscriptions_to_keep:
            self.subscriptions.add(*subscriptions_to_keep)

        self.check_set_subscriptions_131004_done = True
        self.save()

    #
    #
    #
    # ————————————————————————————————————————————————————— End temporary space

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def get_status_attributes(cls):
        try:
            return cls._status_attributes_cache

        except AttributeError:
            # cls._status_attributes_cache = [fname for fname, field
            #                                 in cls._fields.items()
            #                                 if fname.startswith('is_')
            #                                 and isinstance(field,
            #                                                models.BooleanField)]

            cls._status_attributes_cache = [
                k for k in READ_STATUS_DATA.keys()
                if 'list_url' in READ_STATUS_DATA[k]
            ]

            return cls._status_attributes_cache

    # ———————————————————————————————————— Class methods & Mongo/Django related

    def __unicode__(self):
        return _(u'{0}∞{1} (#{2}∞#{3}→#{4}) {5} @{6}').format(
            self.user.username,
            self.item.name[:40] + (self.item.name[40:] and u'…'),
            self.user.id, self.item.id, self.id,
            pgettext_lazy(u'adjective', u'read')
            if self.is_read
            else pgettext_lazy(u'adjective', u'unread'),
            self.rating)

    # —————————————————————————————————————————————————————————————— Properties

    @property
    def is_restricted(self):

        # TODO: not sure if these conditions are OK.
        #       We are in a Read, though. We assume
        #       the calling user is owner. This would
        #       a privacy issue if not, but could still
        #       be needed in some cases (debugging
        #       purposes).

        if self.user.has_staff_access:
            return False

        if self.user.is_staff_or_superuser_and_enabled:
            return False

        if self.is_archived:
            return False

        return any(map(lambda sub: sub.feed.is_restricted,
                   self.subscriptions.all()))

        # TODO: refresh/implement this to avoid fetching content from the
        #       database if the remote article is not available anymore.
        # NOTE: This is clearly overkill in the libre version, as 1flow
        #       is just a personnal RSS / web crawler tool. This makes
        #       sense for legal issues only if 1flow.io is a paid service.
        #
        # delta_from_now = timedelda(now() - self.date_published)
        # if self.is_read:
        #     if self.is_archived:
        #     if self.is_auto_read:
        #         if self.item.feed.restrict_read_delta \
        #           and delta_from_now > self.item.feed.restrict_read_delta:
        #             return True
        #     and delta_from_now <= config.ARTICLE_LIMITS_READ

    @property
    def title(self):

        article = self.item
        feed    = article.a_feed

        if feed:
            source = _(u' ({feed})').format(feed=feed.name)

        else:
            source = u''

        return _(u'{title}{source}').format(title=article.name,
                                            source=source)

    @property
    def get_source(self):

        if self.item.sources.count():
            return self.item.sources.all()

        if self.subscriptions:
            return self.subscriptions.all()

        return self.item.get_source

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
    def reading_time(self):
        """ Return a rounded value of the approximate reading time,
            for the user and the article. """

        wc = self.item.word_count_TRANSIENT

        if wc is None:
            return None

        return wc / self.user.preferences.read.reading_speed

    @property
    def reading_time_display(self):

        rtm = self.reading_time

        if rtm is None:
            return u''

        if rtm == 0:
            return _(u'a quick read')

        return _(u'{0} read').format(naturaldelta(timedelta(seconds=rtm * 60)))

    @property
    def reading_time_abstracted(self):

        rtm = self.reading_time

        if rtm is None:
            return u''

        inum = 1
        icon = u'∎'  # u'<i class="icon-time"></i>'
        tmpl = _(u'<span class="popover-top" data-toggle="tooltip" '
                 u'title="Reading time: {0}">{1}</span>')
        time = naturaldelta(timedelta(seconds=rtm * 60))

        if rtm > 8:
            inum = 4

        elif rtm > 3:
            inum = 3

        elif rtm > 1:
            inum = 2

        elif rtm == 0:
            # HEADS UP: patch/hack; non-breakable spaces everywhere.
            time = _(u'very quick (<1 min)')

        return tmpl.format(time, inum * icon)

    # ————————————————————————————————————————————————————————————————— Methods

    def activate(self, force=False):
        """ This method will mark the Read ``.is_good=True``
            and do whatever in consequence. """

        if not force and not self.item.is_good:
            LOGGER.error(u'Cannot activate read %s, whose article '
                         u'is not ready for public use!', self)
            return

        self.is_good = True
        self.save()

        with statsd.pipeline() as spipe:
            spipe.incr('reads.counts.good')
            spipe.decr('reads.counts.bad')

        self.update_cached_descriptors()

    def remove_tags(self, tags=None):
        """ Remove some tags from a read. `tags` is a list of strings.

        If no tag remains after removal, the read gets back the
        default tags from the article it comes from.
        """

        if tags is None:
            tags = []

        if tags:
            self.tags.remove(*Tag.get_tags_set(tags, origin=self))

        if self.tags == []:
            self.tags.add(*self.item.tags.all())

            # NO update_cached_descriptors() here.

    def add_tags(self, tags):
        """ Add some tags to current read. ``tags`` is a list of strings. """

        self.tags.add(*Tag.get_tags_set(tags, origin=self))

    # ————————————————————————————————————————————— Update subscriptions caches

    def update_cached_descriptors(self, operation=None, update_only=None):

        if operation is None:
            operation = '+'

        assert operation in ('+', '-')

        if operation == '+':
            op = operator.add
        else:
            op = operator.sub

        if update_only is None:

            to_change = ['all_items_count']

            if self.is_archived:
                to_change.append('archived_items_count')

            if self.is_bookmarked:
                to_change.append('bookmarked_items_count')

            if self.is_starred:
                to_change.append('starred_items_count')

            if not self.is_read:
                to_change.append('unread_items_count')

            for watch_attr_name in WATCH_ATTRIBUTES_FIELDS_NAMES:
                if getattr(self, watch_attr_name):
                    # Strip 'is_' from the attribute name.
                    to_change.append(watch_attr_name[3:] + '_items_count')

        else:
            assert type(update_only) in (type(tuple()), type([]))

            to_change = [only + '_items_count' for only in update_only]

            for attr_name in to_change:

                updated_folders = []

                try:
                    for subscription in self.subscriptions.all():
                        setattr(subscription, attr_name,
                                op(getattr(subscription, attr_name), 1))

                except AttributeError, e:
                    LOGGER.warning(u'Skipped subscriptions cache descriptor '
                                   u'update for %s from %s: %s',
                                   attr_name, self, e)

                try:
                    for folder in subscription.folders.all():
                        if folder in updated_folders:
                            continue

                        setattr(folder, attr_name,
                                op(getattr(folder, attr_name), 1))

                        updated_folders.append(folder)

                except AttributeError, e:
                    LOGGER.warning(u'Skipped folder cache descriptor '
                                   u'update for %s from %s: %s',
                                   attr_name, self, e)

                try:
                    setattr(self.user.user_counters, attr_name,
                            op(getattr(self.user.user_counters, attr_name), 1))

                except AttributeError, e:
                    LOGGER.warning(u'Skipped user cache descriptor '
                                   u'update for %s from %s: %s',
                                   attr_name, self, e)

    # ——————————————————————————————————————————————— Boolean attributes change

    def mark_archived(self):
        if self.is_archived_can_change() and not self.is_archived:
            self.is_archived = True
            self.save()

            # no archived_items_count descriptors yet.
            # self.update_cached_descriptors(update_only='archived')

    def is_archived_can_change(self):

        if self.is_archived:
            # A user can always unarchive anything. This is dangerous because
            # he can permanently loose data, but the UI asks for a confirmation
            # in that case.
            return True

        return True

        if self.is_restricted:
            LOGGER.warning(u'Implement real-time checking '
                           u'of archive-ability permission.')

            return True

        else:
            # An unrestricted read/feed can always change status.
            return True

    def is_archived_changed(self):

        self.update_cached_descriptors(operation='+'
                                       if self.is_archived else '-',
                                       update_only=['archived'])

    def is_bookmarked_changed(self):

        self.update_cached_descriptors(operation='+'
                                       if self.is_bookmarked else '-',
                                       update_only=['bookmarked'])

    def is_read_changed(self):

        # HEADS UP: the operation is inverted, we count UNread items.
        self.update_cached_descriptors(operation='-' if self.is_read else '+',
                                       update_only=['unread'])

    def is_starred_changed(self):

        self.update_cached_descriptors(operation='+'
                                       if self.is_starred else '-',
                                       update_only=['starred'])

# ————————————————————————————————————————————————————— Watch attributes change


def gen_attr_is_changed_method(attr_name):

    def attr_is_changed_method(self):

        self.update_cached_descriptors(operation='-'
                                       if getattr(self, attr_name) else '+',
                                       update_only=[attr_name[3:]])

    return attr_is_changed_method

for attr_name in WATCH_ATTRIBUTES_FIELDS_NAMES:
    setattr(Read, attr_name + '_changed',
            gen_attr_is_changed_method(attr_name))


# ————————————————————————————————————————————————————————————————————— Signals


def read_post_save(instance, **kwargs):
    """ Method meant to be run from a celery task. """

    read = instance

    if kwargs.get('created', False):

        with statsd.pipeline() as spipe:
            spipe.incr('reads.counts.total')

            if read.is_good:
                spipe.incr('reads.counts.good')

            else:
                spipe.incr('reads.counts.bad')

        if read.date_created < MIGRATION_DATETIME:
            # HEADS UP: REMOVE THIS WHEN migration is finished
            return

        read.rating = read.item.default_rating

        read.set_subscriptions(commit=False)

    # HEADS UP: this should be done manually in methods like activate().
    #           This will avoid double counting, and users seeing reads
    #           while these reads are not yet "good", and thus not really
    #           available to the user in the interface.
    # read.update_cached_descriptors()
    pass


def read_pre_delete(instance, **kwargs):
    """ before deleting a read, update the subscriptions cached descriptors. """

    read = instance

    with statsd.pipeline() as spipe:
        spipe.decr('reads.counts.total')

        if read.is_good:
            spipe.decr('reads.counts.good')

        else:
            spipe.decr('reads.counts.bad')

    if not read.is_good:
        # counters already don't take this read into account.
        return

    read.update_cached_descriptors(operation='-')


pre_delete.connect(read_pre_delete, sender=Read)
post_save.connect(read_post_save, sender=Read)


# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def Folder_reads_property_get(self):

    # We user `.reads` to get only the owner's good reads.
    return self.user.reads.filter(
        subscriptions__in=self.subscriptions.all())


def BaseItem_good_reads_property_get(self):

    # Do NOT filter on is_good here. The BaseItem needs to
    # know about ALL reads, to activate them when ready.
    return self.reads.filter(is_good=True)


def BaseItem_bad_reads_property_get(self):

    # Do NOT filter on is_good here. The BaseItem needs to
    # know about ALL reads, to activate them when ready.
    return self.reads.filter(is_good=False)


def User_reads_property_get(self):

    return self.all_reads.filter(is_good=True)


Folder.reads        = property(Folder_reads_property_get)
BaseItem.good_reads = property(BaseItem_good_reads_property_get)
BaseItem.bad_reads  = property(BaseItem_bad_reads_property_get)
User.reads          = property(User_reads_property_get)
