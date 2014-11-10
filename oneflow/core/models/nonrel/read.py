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

import sys
import logging
import operator
import feedparser

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, Q, CASCADE
from mongoengine.fields import (StringField, BooleanField,
                                FloatField, DateTimeField,
                                ListField, ReferenceField,
                                GenericReferenceField, DBRef)
from mongoengine.errors import NotUniqueError, ValidationError

# from cache_utils.decorators import cached

from django.conf import settings
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from ....base.utils import register_task_method
from ....base.utils.dateutils import now, timedelta, naturaldelta

from .common import (
    DocumentHelperMixin,  # , CACHE_ONE_DAY
    WATCH_ATTRIBUTES_FIELDS_NAMES,
    READ_STATUS_DATA,
)

from .folder import Folder
from .subscription import Subscription, generic_check_subscriptions_method
from .article import Article
from .user import User
from .tag import Tag

LOGGER                = logging.getLogger(__name__)
feedparser.USER_AGENT = settings.DEFAULT_USER_AGENT


__all__ = ['Read', ]


READ_BOOKMARK_TYPE_CHOICES = (
    (u'U', _(u'Undefined')),
    (u'A', _(u'This afternoon')),
    (u'W', _(u'This week-end')),
)


class Read(Document, DocumentHelperMixin):

    # BIG DB migration 20141028
    bigmig_migrated = BooleanField(default=False)
    bigmig_reassigned = BooleanField(default=False)
    # END BIG DB migration

    user = ReferenceField('User', reverse_delete_rule=CASCADE)
    article = ReferenceField('Article', unique_with='user',
                             reverse_delete_rule=CASCADE)

    # HEADS UP: no `reverse_delete_rule` here, this would be too heavy and
    # slow. The hard work is done in `Subscription.post_delete_task()`.
    subscriptions = ListField(ReferenceField(Subscription))

    senders = ListField(ReferenceField(User), verbose_name=_(u'Senders'),
                        help_text=_(u'All the users that have shared the '
                                    u'article with the current owner of '
                                    u'this read.'))

    date_created = DateTimeField(default=now)

    is_good   = BooleanField(verbose_name=_('good for use?'),
                             help_text=_(u'The system has validated the '
                                         u'underlying article, and the read '
                                         u'can now be shown, used by its '
                                         u'owner, and counted in statistics.'),
                             default=False)

    is_read   = BooleanField(help_text=_(u'The Owner has read the content or '
                             u'has manually marked it as such.'),
                             default=False)
    date_read = DateTimeField()

    is_auto_read   = BooleanField(help_text=_(u'The system has automatically '
                                  u'marked it as read, in respect of a system '
                                  u'rule or a user preference.'), default=False)
    date_auto_read = DateTimeField()

    is_archived   = BooleanField(help_text=_(u'The Owner has archived this '
                                 u'read to explicitely keep it accessible.'),
                                 default=False)
    date_archived = DateTimeField()

    # NOTE: is_starred has no default, because we use True
    #       as "I like it" and False as "I don't like it".
    is_starred   = BooleanField(help_text=_(u'The owner has starred the '
                                u'content, signifying he/she loves it or '
                                u'that it is much of interest for him/her.'))
    date_starred = DateTimeField()

    is_bookmarked   = BooleanField(help_text=_(u'This content is marked to '
                                   u'be read later. When, depends on the '
                                   u'`.bookmark_type` attribute.'),
                                   default=False)
    date_bookmarked = DateTimeField()
    bookmark_type   = StringField(max_length=1, default=u'U',
                                  choices=READ_BOOKMARK_TYPE_CHOICES)

    is_fact   = BooleanField(help_text=_(u'Qualifies a time-dependant fact.'),
                             default=False)
    date_fact = DateTimeField()

    is_quote   = BooleanField(help_text=_(u'Qualifies someone’s words, '
                              u'thoughts or intentions.'), default=False)
    date_quote = DateTimeField()

    is_number   = BooleanField(help_text=_(u'Qualifies explicitely quantized '
                               u'data.'), default=False)
    date_number = DateTimeField()

    is_analysis   = BooleanField(help_text=_(u'Qualifies in-depth analysis, '
                                 u'studies or research publications.'),
                                 default=False)
    date_analysis = DateTimeField()

    is_prospective   = BooleanField(help_text=_(u'Qualifies things that want'
                                    u' to watch, that will happen or not.'),
                                    default=False)
    date_prospective = DateTimeField()

    is_knowhow   = BooleanField(help_text=_(u'Qualifies anything about '
                                u'How-to-do things and profession '
                                u'best-practices.'), default=False)
    date_knowhow = DateTimeField()

    is_rules   = BooleanField(help_text=_(u'Qualifies anything about laws, '
                              u'governments/public regulations.'),
                              default=False)
    date_rules = DateTimeField()

    is_knowledge   = BooleanField(help_text=_(u'Qualifies anything that the '
                                  u'owner wants to retain as a “must know”, '
                                  u'whatever the context.'), default=False)
    date_knowledge = DateTimeField()
    knowledge_type = StringField(max_length=2)

    is_fun   = BooleanField(help_text=_(u'Qualifies anything that makes you '
                            u'laugh out loud.'), default=False)
    date_fun = DateTimeField()

    # TODO: convert to UserTag to use ReferenceField and reverse_delete_rule.
    tags = ListField(GenericReferenceField(),
                     default=list, verbose_name=_(u'Tags'),
                     help_text=_(u'User set of tags for this read.'))

    # This will be set to Article.default_rating
    # until the user sets it manually.
    rating = FloatField()

    # ————————————————————————————————————————————————————————— Temporary space
    # items here will have a limited lifetime.

    # At the time this is created, set_subscriptions() does the right thing.
    # Don't let new reads be checked more than once, the database is already
    # overloaded with post-processing and normal end-users related usage.
    check_set_subscriptions_131004_done = BooleanField(default=True)

    def check_set_subscriptions_131004(self):
        """ Fix a bug where reads had too much subscriptions. """

        if isinstance(self.user, DBRef) or self.user is None:
            self.delete()
            sys.stderr.write(u'u')
            return

        if isinstance(self.article, DBRef) or self.article is None:
            self.delete()
            sys.stderr.write(u'a')
            return

        if self.subscriptions.count() == 1:
            # Don't bother doing CPU-intensive tasks,
            # this one seems good. At least we hope.
            self.update(set__check_set_subscriptions_131004_done=True)

        else:
            subscriptions_to_keep = []

            for subscription in self.subscriptions:
                try:
                    if subscription.user == self.user:
                        subscriptions_to_keep.append(subscription)
                except:
                    sys.stderr.write(u'-')

            # We have to update() because changing the boolean to True
            # doesn't make MongoEngine write it to the database, because
            # the new value is not different from the default one…
            #
            # Then we update subscriptions via the same mechanism to
            # avoid two disctinct write operations on the database.
            #
            # No need to reload, this is a one-shot repair.
            self.update(set__check_set_subscriptions_131004_done=True,
                        set__subscriptions=subscriptions_to_keep)

    # ———————————————————————————————————————————————————————— Class attributes

    watch_attributes = WATCH_ATTRIBUTES_FIELDS_NAMES

    status_data = READ_STATUS_DATA

    meta = {
        'indexes': [
            'user',
            ('user', 'is_good'),
            ('user', 'is_good', 'is_read'),
            ('user', 'is_good', 'is_starred'),
            ('user', 'is_good', 'is_bookmarked'),
            'article',
            ('article', 'is_good'),
            'bigmig_migrated',
            'bigmig_reassigned',
        ]
    }

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
            #                                                BooleanField)]

            cls._status_attributes_cache = [
                k for k in cls.status_data.keys()
                if 'list_url' in cls.status_data[k]
            ]

            return cls._status_attributes_cache

    # ———————————————————————————————————— Class methods & Mongo/Django related

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        read = document

        if created:
            if read._db_name != settings.MONGODB_NAME_ARCHIVE:

                # HEADS UP: this task is declared by
                # the register_task_method call below.
                read_mongo_post_create_task.delay(read.id)  # NOQA

    def mongo_post_create_task(self):
        """ Method meant to be run from a celery task. """

        self.rating = self.article.default_rating

        self.set_subscriptions(commit=False)

        self.save()

        self.update_cached_descriptors()

    @classmethod
    def signal_pre_delete_handler(cls, sender, document, **kwargs):

        read = document

        if not read.is_good:
            # counters already don't take this read into account.
            return

        read.update_cached_descriptors(operation='-')

    def validate(self, *args, **kwargs):
        try:
            super(Read, self).validate(*args, **kwargs)

        except ValidationError as e:
            tags_error = e.errors.get('tags', None)

            if tags_error and 'GenericReferences can only contain documents' \
                    in str(tags_error):

                good_tags  = set()
                to_replace = set()

                for tag in self.tags:
                    if isinstance(tag, Document):
                        good_tags.add(tag)

                    else:
                        to_replace.add(tag)

                new_tags = Tag.get_tags_set([t for t in to_replace
                                            if t not in (u'', None)])

                self.tags = good_tags | new_tags
                e.errors.pop('tags')

            if e.errors:
                raise e

    def __unicode__(self):
        return _(u'{0}∞{1} (#{2}∞#{3}→#{4}) {5} @{6}').format(
            self.user.username,
            self.article.title[:40] + (self.article.title[40:] and u'…'),
            self.user.id, self.article.id, self.id,
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

        if (self.user.is_staff_or_superuser_and_enabled
                and self.user.preferences.staff.allow_all_articles):
            return False

        if self.is_archived:
            return False

        return any(map(lambda sub: sub.feed.restricted, self.subscriptions))

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
        #         if self.article.feed.restrict_read_delta \
        #           and delta_from_now > self.article.feed.restrict_read_delta:
        #             return True
        #     and delta_from_now <= config.ARTICLE_LIMITS_READ

    @property
    def title(self):

        article = self.article
        feed    = article.feed

        if feed:
            source = _(u' ({feed})').format(feed=feed.name)

        else:
            source = u''

        return _(u'{title}{source}').format(title=article.title,
                                            source=source)

    @property
    def get_source(self):

        if self.article.source:
            return self.article.source

        if self.subscriptions:
            # This method displays things to the user. Don't let dead
            # DBRefs pass through.
            #
            # TODO: let things pass through for administrators, though.
            #
            return [s for s in self.subscriptions if isinstance(s, Document)]

        return self.article.get_source

    @property
    def get_source_unicode(self):

        source = self.get_source

        if source.__class__ in (unicode, str):
            return source

        sources_count = len(source)

        if sources_count > 2:
            return _(u'Multiple sources ({0} feeds)').format(sources_count)

        return u' / '.join(x.name for x in source)

    @property
    def reading_time(self):
        """ Return a rounded value of the approximate reading time,
            for the user and the article. """

        wc = self.article.word_count_TRANSIENT

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

    # HEADS UP: this method come from the subscription module.
    check_subscriptions = generic_check_subscriptions_method

    def set_subscriptions(self, commit=True):
        # @all_subscriptions, because here internal feeds count.
        user_feeds         = [sub.feed for sub in self.user.all_subscriptions]
        article_feeds      = [feed for feed in self.article.feeds
                              if feed in user_feeds]

        # HEADS UP: searching only for feed__in=article_feeds will lead
        # to have other user's subscriptions attached to the read.
        # Harmless but very confusing.
        self.subscriptions = list(Subscription.objects(
                                  feed__in=article_feeds,
                                  user=self.user))

        if commit:
            self.save()

            # TODO: only for the new subscriptions.
            #self.update_cached_descriptors( … )

        return self.subscriptions

    def activate(self, force=False):
        """ This method will mark the Read ``.is_good=True``
            and do whatever in consequence. """

        if not force and not self.article.is_good:
            LOGGER.error(u'Cannot activate read %s, whose article '
                         u'is not ready for public use!', self)
            return

        self.is_good = True
        self.save()

        update_only = ['all']

        if self.is_starred:
            update_only.append('starred')

        if self.is_bookmarked:
            update_only.append('bookmarked')

        if not self.is_read:
            update_only.append('unread')

        self.update_cached_descriptors(update_only=update_only)

    def remove_tags(self, tags=[]):
        """ If the user remove his own tags from a Read, it will get back the
            default tags from the article it comes from. """

        if tags:
            for tag in Tag.get_tags_set(tags, origin=self):
                self.update(pull__tags=tag)

            self.safe_reload()

        if self.tags == []:
            self.tags = self.article.tags.copy()
            self.save()
            # NO update_cached_descriptors() here.

    def add_tags(self, tags):

        for tag in Tag.get_tags_set(tags, origin=self):
            self.update(add_to_set__tags=tag)

        self.safe_reload()
        # NO update_cached_descriptors() here.

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

            to_change = ['all_articles_count']

            if self.is_archived:
                to_change.append('archived_articles_count')

            if self.is_bookmarked:
                to_change.append('bookmarked_articles_count')

            if self.is_starred:
                to_change.append('starred_articles_count')

            if not self.is_read:
                to_change.append('unread_articles_count')

            for watch_attr_name in Read.watch_attributes:
                if getattr(self, watch_attr_name):
                    # Strip 'is_' from the attribute name.
                    to_change.append(watch_attr_name[3:] + '_articles_count')

        else:
            assert type(update_only) in (type(tuple()), type([]))

            to_change = [only + '_articles_count' for only in update_only]

            for attr_name in to_change:
                try:

                    updated_folders = []

                    for subscription in self.subscriptions:
                        setattr(subscription, attr_name,
                                op(getattr(subscription, attr_name), 1))

                        for folder in subscription.folders:
                            if folder in updated_folders:
                                continue

                            setattr(folder, attr_name,
                                    op(getattr(folder, attr_name), 1))

                            updated_folders.append(folder)

                    setattr(self.user, attr_name,
                            op(getattr(self.user, attr_name), 1))

                except AttributeError, e:
                    LOGGER.warning(u'Skipped cache descriptor update for %s '
                                   u'from %s: %s', attr_name, self, e)

    def is_read_changed(self):

        self.update_cached_descriptors(operation='-' if self.is_read else '+',
                                       update_only=['unread'])

    def is_starred_changed(self):

        self.update_cached_descriptors(operation='+'
                                       if self.is_starred else '-',
                                       update_only=['starred'])

    def mark_archived(self):
        if self.is_archived_can_change() and not self.is_archived:
            self.is_archived = True
            self.save()

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


register_task_method(Read, Read.mongo_post_create_task,
                     globals(), queue=u'high')

# ————————————————————————————————————————————————————————— external properties
#                                            Defined here to avoid import loops


def Folder_reads_property_get(self):

    # The owner has already filtered good reads via an indexed search.
    #
    # self.subscriptions is a QuerySet, we need
    # to convert it to a list for the new QuerySet.
    return self.owner.reads(subscriptions__in=[s for s in self.subscriptions])


def Subscription_reads_property_get(self):

    # The user has already filtered good reads via an indexed search.
    return self.user.reads(subscriptions__contains=self)


def Article_reads_property_get(self):

    # Do NOT filter on is_good here. The Article needs to
    # know about ALL reads, to activate them when ready.
    return Read.objects.filter(article=self)


def Article_good_reads_property_get(self):

    # Do NOT filter on is_good here. The Article needs to
    # know about ALL reads, to activate them when ready.
    return self.reads(is_good=True)


def Article_bad_reads_property_get(self):

    # Do NOT filter on is_good here. The Article needs to
    # know about ALL reads, to activate them when ready.
    return self.reads(Q(is_good__exists=False) | Q(is_good=False))


def User_reads_property_get(self):

    return Read.objects.filter(user=self, is_good=True)


Folder.reads       = property(Folder_reads_property_get)
Subscription.reads = property(Subscription_reads_property_get)
Article.reads      = property(Article_reads_property_get)
Article.good_reads = property(Article_good_reads_property_get)
Article.bad_reads  = property(Article_bad_reads_property_get)
User.reads         = property(User_reads_property_get)


# —————————————————————————————————————————————————————— external bound methods
#                                            Defined here to avoid import loops


def Subscription_create_read_method(self, article, verbose=True, **kwargs):
    """ Returns a tuple (read, created) with the new (or existing) read,
        and ``created`` as a boolean indicating if it was actually created
        or if it existed before.

    """
    new_read = Read(article=article, user=self.user)

    try:
        new_read.save()

    except (NotUniqueError, DuplicateKeyError):
        if verbose:
            LOGGER.info(u'Duplicate read %s!', new_read)

        cur_read = Read.objects.get(article=article, user=self.user)

        # If another feed has already created the read, be sure the
        # current one is registered in the read via the subscriptions.
        cur_read.update(add_to_set__subscriptions=self)

        #
        # NOTE: we do not check `is_good` here, when the read was not
        #       created. This is handled (indirectly) via the article
        #       check part of Subscription.check_reads(). DRY.
        #

        return cur_read, False

    except:
        # We must not fail here, because often this method is called in
        # a loop 'for subscription in ….subscriptions:'. All other read
        # creations need to succeed.
        LOGGER.exception(u'Could not save read %s!', new_read)

    else:

        # XXX: todo remove this 'is not None', when database is clean…
        tags = [t for t in article.tags if t is not None]

        params = dict(('set__' + key, value)
                      for key, value in kwargs.items())

        # If the article was already there and fetched (mutualized from
        # another feed, for example), activate the read immediately.
        # If we don't do this here, the only alternative is the daily
        # global_reads_checker() task, which is not acceptable for
        # "just-added" subscriptions, whose reads are created via the
        # current method.
        if article.is_good:
            params['set__is_good'] = True

        new_read.update(set__tags=tags,
                        set__subscriptions=[self], **params)

        # Update cached descriptors
        self.all_articles_count += 1
        self.unread_articles_count += 1

        return new_read, True

Subscription.create_read = Subscription_create_read_method
