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

import re
import uuid
import logging

from constance import config

from celery import task

from inspect_model import InspectModel

from mongoengine import Q as MQ
from mongoengine.fields import DBRef

from django.db import IntegrityError
from django.db import connection
# from django.core.exceptions import ObjectDoesNotExist
# from django.utils.translation import ugettext_lazy as _

from sparks.foundations.classes import SimpleObject

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.dateutils import benchmark, now

from ..models.common import (
    USER_FEEDS_SITE_URL,
)

from ..models.reldb import (
    User, Preferences,
    SimpleTag as Tag,
    WebSite,
    Author,

    # BaseFeed,
    RssAtomFeed,
    Article, OriginalData,
    Subscription,
    Read,

    Folder,

    UserFeeds, UserSubscriptions, UserCounters,
    Language,
)

from ..models.nonrel import (
    User as MongoUser,
    Tag as MongoTag,
    WebSite as MongoWebSite,
    Author as MongoAuthor,

    Feed as MongoFeed,
    Article as MongoArticle,
    Subscription as MongoSubscription,
    Read as MongoRead,

    Folder as MongoFolder,
)

LOGGER = logging.getLogger(__name__)

MONGO_INTERNAL_FEED_URL_RE_raw = USER_FEEDS_SITE_URL.replace(
    u'{user.id}', ur'(?P<mongo_uid>\w{24,24})')

MONGO_INTERNAL_FEED_URL_RE = re.compile(MONGO_INTERNAL_FEED_URL_RE_raw)


class StopMigration(Exception):

    """ Raised when the migration must stop immediately. """

    pass


def common_qs_args(qs):
    u""" Make a Mongo QS not cached and immune to timeouts.

    I know “no timeout” is generally a bad practice, but we are in
    a migration; this eases things that are already too complicated.
    """

    return qs.no_cache().timeout(False)

# ————————— Internal caches

feeds_cache = {}
subscriptions_cache = {}
folders_cache = {}
authors_cache = {}
tags_cache = {}
languages_cache = {}
articles_ids_cache = {}

# —————————————————————————————————————————————————————————— Migration counters

# Allow internal function to write counters
# without passing them as argument everytime.
counters = SimpleObject()

all_websites = common_qs_args(MongoWebSite.objects.all())
all_websites_count = all_websites.count()
counters.created_websites_count = 0
counters.migrated_websites_count = 0

all_authors = common_qs_args(MongoAuthor.objects.all())
all_authors_count = all_authors.count()
counters.created_authors_count = 0
counters.migrated_authors_count = 0

all_users = common_qs_args(MongoUser.objects.all())
all_users_count = all_users.count()
# created_users_count = 0  # We can't know; pseudo-computed later
counters.migrated_users_count = 0

all_feeds = common_qs_args(MongoFeed.objects.all())
all_feeds_count = all_feeds.count()
counters.created_feeds_count = 0
counters.migrated_feeds_count = 0

all_tags = common_qs_args(MongoTag.objects.all())
all_tags_count = all_tags.count()
counters.created_tags_count = 0
counters.migrated_tags_count = 0

all_articles = common_qs_args(MongoArticle.objects.all())
all_articles_count = all_articles.count()
counters.created_articles_count = 0
counters.migrated_articles_count = 0

all_folders = common_qs_args(MongoFolder.objects.all())
all_folders_count = all_folders.count()
counters.created_folders_count = 0
counters.migrated_folders_count = 0

all_subscriptions = common_qs_args(MongoSubscription.objects.all())
all_subscriptions_count = all_subscriptions.count()
counters.created_subscriptions_count = 0
counters.migrated_subscriptions_count = 0

all_reads = common_qs_args(MongoRead.objects.all())
all_reads_count = all_reads.count()
counters.created_reads_count = 0
counters.migrated_reads_count = 0

counters.reassigned_objects_count = 0
counters.reassigned_tags_count = 0
counters.failed_objects_count = 0

# ——————————————————————————————————————————————————————————————————— Shortcuts


get_tag = Tag.objects.get


# —————————————————————————————————————————————————————————— Utils & QS filters


def vacuum_analyze(message=None):
    """ Help PG staying fresh. """

    if config.CHECK_DATABASE_MIGRATION_VACUUM_ENABLED:
        with benchmark('VACUUMING DATABASE… {0}'.format(
                       u'' if message is None else message)):
            cursor = connection.cursor()
            cursor.execute('VACUUM ANALYZE;')


def not_yet_migrated(mongo_queryset):
    """ Filter documents which are not yet migrated. """

    return mongo_queryset.filter(
        MQ(bigmig_migrated__exists=False) | MQ(bigmig_migrated=False))


def no_tags_reassigned(mongo_queryset):
    """ Filter documents on which tags are not yet reassigned. """

    return mongo_queryset.filter(MQ(bigmig_reassigned__exists=False)
                                 | MQ(bigmig_reassigned=False))


def master_documents(mongo_queryset):
    """ Filter documents which are not duplicates of another. """

    return mongo_queryset.filter(MQ(duplicate_of__exists=False)
                                 | MQ(duplicate_of=None))


# ———————————————————————————————————————————————————— Get equivalent instances


def get_language_from_mongo_language(mongo_language):
    """ Find an language in PG from one in MongoDB. """

    try:
        return languages_cache[mongo_language]

    except KeyError:
        language = Language.get_by_code(mongo_language)

        languages_cache[mongo_language] = language

        return language


def get_author_from_mongo_author(mongo_author):
    """ Find an author in PG from one in MongoDB. """

    try:
        return authors_cache[mongo_author.id]

    except KeyError:
        author = Author.objects.get(
            origin_name=mongo_author.origin_name,
            website=WebSite.objects.get(url=mongo_author.website.url))

        authors_cache[mongo_author.id] = author

        return author


def get_article_from_mongo_article(mongo_article):
    """ Find an article in PG from one in MongoDB. """

    try:
        article = Article.objects.get(id=articles_ids_cache[mongo_article.id])

    except KeyError:
        article = Article.objects.get(url=mongo_article.url)
        articles_ids_cache[mongo_article.id] = article.id

    return article


def get_read_from_mongo_read(mongo_read):
    """ Find a read in PG from one in MongoDB. """

    return Read.objects.get(
        item=get_article_from_mongo_article(mongo_read.article),
        user=mongo_read.user.django,
    )


def get_folder_from_mongo_folder(mongo_folder):
    """ Get the PG equivalent of a mongodb folder. """

    try:
        return folders_cache[mongo_folder.id]

    except KeyError:
        folder = Folder.objects.get(
            name=mongo_folder.name,
            user=mongo_folder.owner.django,
            parent=None if mongo_folder.parent is None
            else get_folder_from_mongo_folder(mongo_folder.parent)
        )

        folders_cache[mongo_folder.id] = folder

    return folder


def get_feed_from_mongo_feed(mongo_feed):
    """ Return the PG equivalent of a mongoDB feed, internal or not. """

    try:
        return feeds_cache[mongo_feed.id]

    except KeyError:
        if mongo_feed.is_internal:
            feed = get_internal_feed_from_mongo_feed(mongo_feed)

        else:
            feed = RssAtomFeed.objects.get(url=mongo_feed.url)

        feeds_cache[mongo_feed.id] = feed

        return feed


def get_internal_feed_from_mongo_feed(mongo_feed):
    """ Get the PostgreSQL equivalent of a MongoEngine internal feed. """

    match = MONGO_INTERNAL_FEED_URL_RE.match(mongo_feed.url)

    # LOGGER.debug(u'>>>>>>>>>>')
    # LOGGER.debug(u'Looking up internal feed from %s', mongo_feed)
    # LOGGER.debug(mongo_feed.url)
    # LOGGER.debug(MONGO_INTERNAL_FEED_URL_RE_raw)
    # LOGGER.debug(match.group('uid'))
    # LOGGER.debug(u'<<<<<<<<<<')

    mongo_uid = match.group('mongo_uid')
    mongo_user = MongoUser.objects.get(id=mongo_uid)

    # This is probably not the best way of
    # finding which feed it is, but it works:

    if mongo_feed == mongo_user.web_import_feed:
        return mongo_user.django.user_feeds.imported_items

    if mongo_feed == mongo_user.sent_items_feed:
        return mongo_user.django.user_feeds.sent_items

    if mongo_feed == mongo_user.received_items_feed:
        return mongo_user.django.user_feeds.received_items

    # NOTE: there are no `written_items` in the MongoDB database.

    raise StopMigration(u'Did not find any matching internal '
                        u'feed, this should not happen.')


def get_subscription_from_mongo_subscription(mongo_subscription):
    """ Return the PG equivalent of a mongoDB subscription, internal or not. """

    try:
        return subscriptions_cache[mongo_subscription.id]

    except KeyError:
        subscription = Subscription.objects.get(
            user=mongo_subscription.user.django,
            feed=get_feed_from_mongo_feed(mongo_subscription.feed)
        )

        subscriptions_cache[mongo_subscription.id] = subscription

        return subscription


def get_tags_from_mongo_tags(mongo_tags):
    """ Return a PG Tag set from a mongo tags iterable. """

    tags = set()

    for mongo_tag in mongo_tags:
        try:
            tag = tags_cache[mongo_tag.id]

        except KeyError:
            tag = get_tag(name=mongo_tag.name)

            tags_cache[mongo_tag.id] = tag

        tags.add(tag)

    return tags

# —————————————————————————————————————————————————————————————— Migrate models


def migrate_user_and_preferences(mongo_user):
    """  Migrate a user and his/her preferences from mongdb to PG. """

    try:
        user = mongo_user.django

    except User.DoesNotExist:
        user = User(id=mongo_user.django_user,
                    username=mongo_user.username,
                    email=u'{0}@migration.1flow.io'.format(
                        mongo_user.username))

        try:
            user.save()

        except IntegrityError:
            # The same username already exists. Just
            # update the Mongo One to match the ID.
            return None, None

    # If already existing, preferences could have not been created yet.
    try:
        preferences = user.preferences

    except Preferences.DoesNotExist:
        preferences = Preferences(user=user)
        preferences.save()

    preferences.check()

    # user.save()

    preferences = user.preferences
    mongo_preferences = mongo_user.preferences

    imp = InspectModel(type(preferences))

    for preference_name in [f for f in imp.relation_fields if f != 'user']:

        preference = getattr(preferences, preference_name)
        mongo_preference = getattr(mongo_preferences, preference_name)

        im = InspectModel(type(preference))

        for field_name in im.fields:
            try:
                pref_value = getattr(mongo_preference, field_name)

            except AttributeError:
                LOGGER.exception(u'Could not get preference %s.%s of user %s',
                                 preference_name, field_name, mongo_user)

            setattr(preference, field_name, pref_value)

    return user, False


def migrate_website(mongo_website):
    """  Migrate a website from mongdb to PG. """

    try:
        return WebSite.objects.get(url=mongo_website.url), False

    except WebSite.DoesNotExist:
        pass

    website = WebSite(
        name=mongo_website.name or u'Website at {0}'.format(mongo_website.url),
        slug=mongo_website.slug or uuid.uuid4().hex,
        url=mongo_website.url,
    )

    # We assume the master is already created.
    # See the master migration task for details.
    if mongo_website.duplicate_of:
        website.duplicate_of = WebSite.objects.get(
            url=mongo_website.duplicate_of.url)

    website.save()

    return website, True


def migrate_author(mongo_author):
    """  Migrate an author from mongdb to PG. """

    try:
        return get_author_from_mongo_author(mongo_author), False

    except Author.DoesNotExist:
        pass

    author = Author(
        name=mongo_author.name,
        origin_name=mongo_author.origin_name,
        website=WebSite.objects.get(url=mongo_author.website.url),
        is_unsure=mongo_author.is_unsure,
    )

    # We assume the master is already created.
    # See the master migration task for details.
    if mongo_author.duplicate_of:
        author.duplicate_of = Author.objects.get(
            url=mongo_author.duplicate_of.url)

    # HEADS UP: the mongo “user” is not the creator,
    #           it's the 1flow account who claimed to
    #           be this author. It's one schema
    #           difference between PG & Mongo archs.
    if mongo_author.user:
        author.users.add(mongo_author.user.django)

    author.save()

    authors_cache[mongo_author.id] = author

    return author, True


def migrate_feed(mongo_feed):
    """  Migrate a non-internal feed from mongdb to PG. """

    try:
        return get_feed_from_mongo_feed(mongo_feed), False

    except RssAtomFeed.DoesNotExist:
        pass

    feed = RssAtomFeed(
        name=mongo_feed.name,
        slug=mongo_feed.slug,
        url=mongo_feed.url,
        is_restricted=mongo_feed.restricted,

        date_created=mongo_feed.date_added,
        # `is_internal` is left untouched,
        # it's another function's job.

        is_active=not mongo_feed.closed,
        is_good=mongo_feed.good_for_use,
        fetch_interval=mongo_feed.fetch_interval,
        date_last_fetch=mongo_feed.last_fetch,

        last_etag=mongo_feed.last_etag,
        last_modified=mongo_feed.last_modified,
    )

    # We assume the master is already created.
    # See the master migration task for details.
    if mongo_feed.duplicate_of:
        feed.duplicate_of = get_feed_from_mongo_feed(mongo_feed.duplicate_of)

    if mongo_feed.created_by:
        feed.user = mongo_feed.created_by.django

    feed.errors = mongo_feed.errors

    # Not really used.
    # feed.options = mongo_feed.options

    if mongo_feed.closed:
        feed.closed_reason = mongo_feed.closed_reason
        feed.date_closed   = mongo_feed.date_closed

    if mongo_feed.thumbnail_url:
        feed.thumbnail_url = mongo_feed.thumbnail_url

    if mongo_feed.description_fr:
        feed.description_fr = mongo_feed.description_fr

    if mongo_feed.description_en:
        feed.description_en = mongo_feed.description_en

    feed.notes = mongo_feed.notes

    #
    # HEADS UP: we voluntarily forget about tags, they will be assigned later.
    #

    feed.save()

    feeds_cache[mongo_feed.id] = feed

    return feed, True


def migrate_article(mongo_article):
    """ Migrate a MongoDB article into PostgreSQL. """

    try:
        article = get_article_from_mongo_article(mongo_article)

    except Article.DoesNotExist:
        article = Article(

            # BaseItem
            name=mongo_article.title or u'Article from {0}'.format(
                mongo_article.url),

            # UrlItem
            url=mongo_article.url,
        )

    else:
        # Has the article been created by a feed refresh ?
        # If so, data must be transfered, else we are going
        # to create a duplicate.
        if article.date_created <= mongo_article.date_added:
            return article, False

    # BaseItem
    # article.name is already set at creation
    article.origin = mongo_article.origin_type
    article.date_published = mongo_article.date_published
    article.is_restricted = mongo_article.is_restricted
    article.default_rating = mongo_article.default_rating
    article.text_direction = mongo_article.text_direction

    # Reset the creation date to match the old database.
    article.date_created = mongo_article.date_added

    if mongo_article.language:
        article.language = get_language_from_mongo_language(
            mongo_article.language)

    # UrlItem
    # article.url is already set at creation
    article.is_orphaned = mongo_article.orphaned
    article.url_absolute = mongo_article.url_absolute
    article.url_error = mongo_article.url_error \
        if mongo_article.url_error != u'' else None

    # ContentItem
    article.image_url = mongo_article.image_url
    article.excerpt = mongo_article.excerpt
    article.content = mongo_article.content
    article.content_type = mongo_article.content_type
    article.content_error = mongo_article.content_error \
        if mongo_article.content_error != u'' else None

    # Needed for ManyToManyField() to succeed.
    article.save()

    needs_save = False

    if mongo_article.duplicate_of:
        article.duplicate_of = get_article_from_mongo_article(
            mongo_article.duplicate_of)
        needs_save = True

    if mongo_article.authors:
        authors = []

        for mongo_author in mongo_article.authors:
            authors.append(get_author_from_mongo_author(mongo_author))

        article.authors.add(*authors)

    if mongo_article.source:
        try:
            Article.sources.add(
                get_article_from_mongo_article(mongo_article.source)
            )
            needs_save = True

        except:
            LOGGER.exception(u'Could not reassign source on article %s '
                             u'(skipped)', article.id)

    feeds = []

    for mongo_feed in mongo_article.feeds:
        if isinstance(mongo_feed, DBRef):
            LOGGER.warning(u'Dangling DBRef %s to a non-existing feed '
                           u'in article %s (skipped)',
                           mongo_feed.id, mongo_article.id)

        else:
            feeds.append(get_feed_from_mongo_feed(mongo_feed))

    if feeds:
        # LOGGER.debug(u'Feeds for article %s: %s', article, feeds)
        article.feeds.add(*feeds)

    # NOT even used in the old database…
    #
    #       pages_url
    #       word_count
    #       publishers

    # REASSIGNED later
    #
    #       tags

    mongo_original_data = mongo_article.original_data

    od_needs_save = False

    try:
        original_data = article.original_data

    except OriginalData.DoesNotExist:
        original_data = OriginalData(item=article)
        od_needs_save = True

    for attr_name in ('google_reader', 'feedparser', ):
        data = getattr(mongo_original_data, attr_name, None)

        if data:
            setattr(original_data, attr_name, data)
            od_needs_save = True

    if od_needs_save:
        original_data.save()

    if needs_save:
        article.save()

    articles_ids_cache[mongo_article.id] = article.id

    return article, True


def migrate_folder(mongo_folder, only_parent=False):
    """ Migrate a Folder from MongoDB to PostgreSQL. """

    # HEADS UP: we manually avoid to go up to __root__, else it will create
    #           __root__ folders indefinitely, or crash at some point.
    if mongo_folder.name == u'__root__':
        return Folder.get_root_for(mongo_folder.owner.django), False

    if mongo_folder.parent:
        parent, created = migrate_folder(mongo_folder.parent,
                                         only_parent=True)

    else:
        parent = None

    # This is a get_or_create() equivalent, but better.
    folder, created = Folder.add_folder(
        name=mongo_folder.name,
        user=mongo_folder.owner.django,
        parent=parent,
    )

    folders_cache[mongo_folder.id] = folder

    if only_parent:
        return folder, False

    if mongo_folder.children:
        children = []

        for mongo_child in mongo_folder.children:
            child, created = migrate_folder(mongo_child)
            children.append(child)

        folder.children.add(*children)

    return folder, False


def migrate_subscription(mongo_subscription):
    """ Migrate a subscription from MongoDB to PostgreSQL. """

    user = mongo_subscription.user.django

    # HEADS UP: perhaps it's an internal feed;
    #           RssAtomFeed.objects.get() won't work.
    feed = get_feed_from_mongo_feed(mongo_subscription.feed)

    try:
        return Subscription.objects.get(user=user, feed=feed), False

    except Subscription.DoesNotExist:
        pass

    subscription = Subscription(
        user=user,
        feed=feed,
        name=mongo_subscription.name,
    )

    subscription.save()

    subscriptions_cache[mongo_subscription.id] = subscription

    # tags: LATER, re-assigned in another migration part.

    if mongo_subscription.folders:
        folders = []

        for mongo_folder in mongo_subscription.folders:
            folders.append(get_folder_from_mongo_folder(mongo_folder))

        subscription.folders.add(*folders)

    return subscription, True


def migrate_read(mongo_read):
    """ Migrate a read from MongoDB to PostgreSQL. """

    user = mongo_read.user.django
    item = get_article_from_mongo_article(mongo_read.article)

    try:
        read = Read.objects.get(user=user, item=item)

    except Read.DoesNotExist:
        pass

        read = Read(
            user=user,
            item=item,
        )

    else:
        # Has the article been created by a feed refresh ?
        # If so, data must be transfered, else we are going
        # to create a duplicate.
        if read.date_created <= mongo_read.date_created:
            return read, False

    read.date_created = mongo_read.date_created
    read.is_good = mongo_read.is_good

    read.is_read = mongo_read.is_read
    read.date_read = mongo_read.date_read
    read.is_auto_read = mongo_read.is_auto_read
    read.date_auto_read = mongo_read.date_auto_read
    read.is_archived = mongo_read.is_archived
    read.date_archived = mongo_read.date_archived
    read.is_starred = mongo_read.is_starred
    read.date_starred = mongo_read.date_starred
    read.is_bookmarked = mongo_read.is_bookmarked
    read.date_bookmarked = mongo_read.date_bookmarked
    read.bookmark_type = mongo_read.bookmark_type

    read.is_fact = mongo_read.is_fact
    read.date_fact = mongo_read.date_fact
    read.is_quote = mongo_read.is_quote
    read.date_quote = mongo_read.date_quote
    read.is_number = mongo_read.is_number
    read.date_number = mongo_read.date_number
    read.is_analysis = mongo_read.is_analysis
    read.date_analysis = mongo_read.date_analysis
    read.is_prospective = mongo_read.is_prospective
    read.date_prospective = mongo_read.date_prospective
    read.is_knowhow = mongo_read.is_knowhow
    read.date_knowhow = mongo_read.date_knowhow
    read.is_rules = mongo_read.is_rules
    read.date_rules = mongo_read.date_rules
    read.is_knowledge = mongo_read.is_knowledge
    read.date_knowledge = mongo_read.date_knowledge
    read.knowledge_type = mongo_read.knowledge_type
    read.is_fun = mongo_read.is_fun
    read.date_fun = mongo_read.date_fun

    read.rating = mongo_read.rating

    read.save()

    # senders is not yet used in MongoDB.

    # tags: LATER, re-assigned in another migration part.

    subscriptions = []

    for mongo_subscription in mongo_read.subscriptions:

        if isinstance(mongo_subscription, DBRef):
            LOGGER.warning(u'Dangling DBRef %s to a non-existing subscription '
                           u'in read %s (skipped)', mongo_subscription.id,
                           mongo_read.id)

        else:
            subscriptions.append(
                get_subscription_from_mongo_subscription(mongo_subscription))

    read.subscriptions.add(*subscriptions)

    return read, True


def migrate_tag(mongo_tag):
    """ Migrate a tag from mongodb to PostgreSQL. """

    #
    # HEADS UP: we always try to get_or_create(), because our current
    #           PG DB can already have the tag even if not migrated.
    #
    tag, created = Tag.objects.get_or_create(
        name=mongo_tag.name,
    )

    if mongo_tag.language != u'':
        tag.language = get_language_from_mongo_language(mongo_tag.language)

    #
    # HEADS UP: parents / children is not implemented for tags, we have none
    #           in the production database as of 20141028.

    if mongo_tag.origin is not None:
        origin = mongo_tag.origin

        if isinstance(origin, MongoFeed):

            pg_origin = get_feed_from_mongo_feed(origin)

        elif isinstance(origin, MongoArticle):

            pg_origin = get_article_from_mongo_article(origin)

        elif isinstance(origin, MongoSubscription):

            pg_origin = get_subscription_from_mongo_subscription(origin)

        elif isinstance(origin, MongoRead):

            pg_origin = get_read_from_mongo_read(origin)

        else:
            LOGGER.warning(u'Unhandled origin: %s for tag %s', origin, tag)
            pg_origin = None

        if pg_origin:
            tag.origin = pg_origin

    tag.save()

    tags_cache[mongo_tag.id] = tag

    return tag, created


# ——————————————————————————————————————————————————————————————— Reassign tags


def reassign_tags_on_feed(mongo_feed):
    """ Set the same tags on a PG feed that are on a mongo one. """

    feed = get_feed_from_mongo_feed(mongo_feed)

    tags = get_tags_from_mongo_tags(mongo_feed.tags)

    feed.tags.add(*tags)

    return len(tags)


def reassign_tags_on_subscription(mongo_subscription):
    """ Set the same tags on a PG subscription that are on a mongo one. """

    subscription = get_subscription_from_mongo_subscription(mongo_subscription)

    tags = get_tags_from_mongo_tags(mongo_subscription.tags)

    subscription.tags.add(*tags)

    return len(tags)


def reassign_tags_on_article(mongo_article):
    """ Set the same tags on a PG article that are on a mongo one. """

    article = get_article_from_mongo_article(mongo_article)

    tags = get_tags_from_mongo_tags(mongo_article.tags)

    article.tags.add(*tags)

    return len(tags)


def reassign_tags_on_read(mongo_read):
    """ Set the same tags on a PG read that are on a mongo one. """

    read = get_read_from_mongo_read(mongo_read)

    tags = get_tags_from_mongo_tags(mongo_read.tags)

    read.tags.add(*tags)

    return len(tags)


# ———————————————————————————————————————————————— Models groups migrations


# NOT NEEDED: def migrate_users_and_preferences(users):


def migrate_websites(websites, stop_on_exception=True, verbose=False):
    """ Migrate websites. """

    for mongo_website in not_yet_migrated(websites):
        try:
            website, created = migrate_website(mongo_website)

        except:
            LOGGER.exception(u'Could not migrate website %s',
                             mongo_website.id)

            if stop_on_exception:
                raise StopMigration('website')

            else:
                continue

        else:
            if verbose:
                LOGGER.info(u'Migrated website %s → %s', mongo_website, website)

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_website.update(set__bigmig_migrated=True)

        if created:
            counters.created_websites_count += 1

        counters.migrated_websites_count += 1

        if counters.migrated_websites_count % 1000 == 0:
            vacuum_analyze(u'(at {0} websites)'.format(
                counters.migrated_websites_count))


def migrate_authors(authors, stop_on_exception=True, verbose=False):
    """ Migrate authors. """

    for mongo_author in not_yet_migrated(authors):
        try:
            author, created = migrate_author(mongo_author)

        except:
            LOGGER.exception(u'Could not migrate author %s',
                             mongo_author.id)

            if stop_on_exception:
                raise StopMigration('author')

            else:
                continue

        else:
            if verbose:
                LOGGER.info(u'Migrated author %s → %s', mongo_author, author)

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_author.update(set__bigmig_migrated=True)

        if created:
            counters.created_authors_count += 1

        counters.migrated_authors_count += 1

        if counters.migrated_authors_count % 10000 == 0:
            vacuum_analyze(u'(at {0} authors)'.format(
                counters.migrated_authors_count))


def migrate_feeds(feeds, stop_on_exception=True, verbose=False):
    """ Migrate feeds. """

    for mongo_feed in not_yet_migrated(feeds):
        try:
            feed, created = migrate_feed(mongo_feed)

        except:
            LOGGER.exception(u'Could not migrate feed %s', mongo_feed.id)

            if stop_on_exception:
                raise StopMigration('feed')

            else:
                continue

        else:
            if verbose:
                LOGGER.info(u'Migrated feed %s → %s', mongo_feed, feed)

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_feed.update(set__bigmig_migrated=True)

        if created:
            counters.created_feeds_count += 1

        counters.migrated_feeds_count += 1

        if counters.migrated_feeds_count % 500 == 0:
            vacuum_analyze(u'(at {0} feeds)'.format(
                counters.migrated_feeds_count))


# NOT NEEDED: def migrate_folders(folders):


# NOT NEEDED: def migrate_subscriptions(subscriptions):


def migrate_articles(articles, stop_on_exception=True, verbose=False):
    """ Migrate articles. """

    for mongo_article in not_yet_migrated(articles):
        try:
            article, created = migrate_article(mongo_article)

        except:
            LOGGER.exception(u'Could not migrate article %s',
                             mongo_article.id)

            if stop_on_exception:
                raise StopMigration('article')

            else:
                continue

        else:
            if verbose:
                LOGGER.info(u'Migrated article %s → %s', mongo_article, article)

            # Avoid too much messing with multiple
            # parallel requests for too little benefit.
            #
            # migrate_reads(mongo_article.reads)

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_article.update(set__bigmig_migrated=True)

        if created:
            counters.created_articles_count += 1

        counters.migrated_articles_count += 1

        if counters.migrated_articles_count % 10000 == 0:
            vacuum_analyze(u'(at {0} articles)'.format(
                counters.migrated_articles_count))


def migrate_reads(mongo_reads, stop_on_exception=True, verbose=False):
    """ Migrate reads from MongoDB to PostgreSQL. """

    for mongo_read in not_yet_migrated(mongo_reads):

        try:
            read, created = migrate_read(mongo_read)

        except:
            LOGGER.exception(u'Could not migrate read %s', mongo_read.id)

            if stop_on_exception:
                raise StopMigration('read')

            else:
                continue

        else:
            if verbose:
                LOGGER.info(u'Migrated read %s → %s', mongo_read, read)

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_read.update(set__bigmig_migrated=True)

        if created:
            counters.created_reads_count += 1

        counters.migrated_reads_count += 1

        if counters.migrated_reads_count % 100000 == 0:
            vacuum_analyze(u'(at {0} reads)'.format(
                counters.migrated_reads_count))


def migrate_tags(tags, stop_on_exception=True, verbose=False):
    """ Migrate tags. """

    for mongo_tag in not_yet_migrated(tags):
        try:
            tag, created = migrate_tag(mongo_tag)

        except:
            LOGGER.exception(u'Could not migrate tag %s', mongo_tag.id)

            if stop_on_exception:
                raise StopMigration('tag')

            else:
                continue

        else:
            if verbose:
                LOGGER.info(u'Migrated tag %s → %s', mongo_tag, tag)

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_tag.update(set__bigmig_migrated=True)

        if created:
            counters.created_tags_count += 1

        counters.migrated_tags_count += 1

        if counters.migrated_tags_count % 5000 == 0:
            vacuum_analyze(u'(at {0} tags)'.format(
                counters.migrated_tags_count))


# ——————————————————————————————————————————————————————————— Tags re-assigning


def reassign_tags_on_feeds(stop_on_exception=True, verbose=False):
    """ Re-assign tags on feeds. """

    LOGGER.info(u'Starting to reassign tags on feeds at %s…', now())

    for feed in no_tags_reassigned(all_feeds):
        try:
            counters.reassigned_tags_count += \
                reassign_tags_on_feed(feed)
            counters.reassigned_objects_count += 1

        except:
            counters.failed_objects_count += 1
            LOGGER.exception(u'Could not reassign tags on feed %s', feed.id)

            if stop_on_exception:
                raise StopMigration('reassign tags on feed')

            else:
                continue

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            feed.update(set__bigmig_reassigned=True)


def reassign_tags_on_subscriptions(stop_on_exception=True, verbose=False):
    """ Re-assign tags on subscriptions. """

    LOGGER.info(u'Starting to reassign tags on subscriptions at %s…', now())

    for subscription in no_tags_reassigned(all_subscriptions):
        try:
            counters.reassigned_tags_count += \
                reassign_tags_on_subscription(subscription)
            counters.reassigned_objects_count += 1

        except:
            counters.failed_objects_count += 1
            LOGGER.exception(u'Could not reassign tags on '
                             u'subscription %s', subscription.id)

            if stop_on_exception:
                raise StopMigration('reassign tags on subscription')

            else:
                continue

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            subscription.update(set__bigmig_reassigned=True)


def reassign_tags_on_articles(stop_on_exception=True, verbose=False):
    """ Re-assign tags on articles. """

    LOGGER.info(u'Starting to reassign tags on articles at %s…', now())

    for article in no_tags_reassigned(all_articles):
        try:
            counters.reassigned_tags_count += \
                reassign_tags_on_article(article)
            counters.reassigned_objects_count += 1

        except:
            counters.failed_objects_count += 1
            LOGGER.exception(u'Could not reassign tags on article %s',
                             article.id)

            if stop_on_exception:
                raise StopMigration('reassign tags on article')

            else:
                continue

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            article.update(set__bigmig_reassigned=True)


def reassign_tags_on_reads(stop_on_exception=True, verbose=False):
    """ Re-assign tags on reads. """

    LOGGER.info(u'Starting to reassign tags on reads at %s…', now())

    for read in no_tags_reassigned(all_reads):
        try:
            counters.reassigned_tags_count += \
                reassign_tags_on_read(read)
            counters.reassigned_objects_count += 1

        except:
            counters.failed_objects_count += 1
            LOGGER.exception(u'Could not reassign tags on read %s', read.id)

            if stop_on_exception:
                raise StopMigration('reassign tags on read')

            else:
                continue

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            read.update(set__bigmig_reassigned=True)


# ——————————————————————————————————————————————————————— Models migrations


def migrate_all_users_and_preferences(stop_on_exception=True, verbose=False):
    """ Migrate things. """

    LOGGER.info(u'Starting to migrate users and preferences at %s…', now())

    for mongo_user in not_yet_migrated(all_users):

        try:
            user, created = migrate_user_and_preferences(mongo_user)

        except:
            LOGGER.exception(u'Could not migrate user %s', mongo_user.id)

            if stop_on_exception:
                raise StopMigration('user')

            else:
                continue

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_user.update(set__bigmig_migrated=True)

        counters.migrated_users_count += 1

        if counters.migrated_users_count % 25 == 0:
            vacuum_analyze(u'(at {0} users)'.format(
                counters.migrated_users_count))

    LOGGER.info(u'Users migrated: {0}/{1}.'.format(
                counters.migrated_users_count,
                all_users_count,
                ))


def migrate_all_websites(stop_on_exception=True, verbose=False):
    """ Migrate things. """

    LOGGER.info(u'Starting to migrate web sites at %s…', now())

    masters_websites = master_documents(all_websites)
    # masters_websites_count = masters_websites.count()

    migrate_websites(masters_websites,
                     stop_on_exception=stop_on_exception,
                     verbose=verbose)

    duplicates_websites = all_websites.filter(duplicate_of__ne=None)
    duplicates_websites_count = duplicates_websites.count()

    migrate_websites(duplicates_websites,
                     stop_on_exception=stop_on_exception,
                     verbose=verbose)

    LOGGER.info(u'Web sites migrated: {0}/{1}, '
                u'{2} dupes, {3} already there.'.format(
                    counters.migrated_websites_count,
                    all_websites_count,
                    duplicates_websites_count,
                    counters.migrated_websites_count
                    - counters.created_websites_count
                ))


def migrate_all_authors(stop_on_exception=True, verbose=False):
    """ Migrate things. """

    LOGGER.info(u'Starting to migrate authors at %s…', now())

    masters_authors = master_documents(all_authors)
    # masters_authors_count = masters_authors.count()

    migrate_authors(masters_authors,
                    stop_on_exception=stop_on_exception,
                    verbose=verbose)

    duplicates_authors = all_authors.filter(duplicate_of__ne=None)
    duplicates_authors_count = duplicates_authors.count()

    migrate_authors(duplicates_authors,
                    stop_on_exception=stop_on_exception,
                    verbose=verbose)

    LOGGER.info(u'Authors migrated: {0}/{1}, '
                u' {2} dupes, {3} already there.'.format(
                    counters.migrated_authors_count,
                    all_authors_count,
                    duplicates_authors_count,
                    counters.migrated_authors_count
                    - counters.created_authors_count
                ))


def migrate_all_feeds(stop_on_exception=True, verbose=False):
    """ Migrate things. """

    LOGGER.info(u'Starting to migrate feeds at %s…', now())

    external_feeds = all_feeds.filter(MQ(is_internal__exists=False)
                                      | MQ(is_internal=False))
    external_feeds_count = external_feeds.count()

    # ————————————————————————————————————————————————————————————— masters

    master_external = master_documents(external_feeds)

    migrate_feeds(master_external,
                  stop_on_exception=stop_on_exception,
                  verbose=verbose)

    # —————————————————————————————————————————————————————————— duplicates

    duplicates_external = external_feeds.filter(duplicate_of__ne=None)
    duplicates_external_count = duplicates_external.count()

    migrate_feeds(duplicates_external,
                  stop_on_exception=stop_on_exception,
                  verbose=verbose)

    # ————————————————————————————————————————————————————————————————— end

    LOGGER.info(u'RSS/Atom feeds migrated: {0}/{1} external, '
                u'skipped {2} internal, {3} dupes, {4} already there.'.format(
                    counters.migrated_feeds_count,
                    external_feeds_count,
                    all_feeds_count - external_feeds_count,
                    duplicates_external_count,
                    counters.migrated_feeds_count
                    - counters.created_feeds_count))


def check_internal_users_feeds_and_subscriptions(stop_on_exception=True,
                                                 verbose=False):
    """ Create internal feeds and subscriptions for all users. """

    LOGGER.info(u'Starting to check internal feeds & subscriptions at %s…',
                now())

    # These are django models.
    current_users_count = User.objects.all().count()
    internal_feeds_count = UserFeeds.objects.all().count()

    for mongo_user in all_users:
        try:
            dj_user = mongo_user.django

        except:
            LOGGER.warning(u'%s does not have a django equivalent.',
                           mongo_user)
            continue

        try:
            user_counters = dj_user.user_counters

        except:
            user_counters = UserCounters(user=dj_user)
            user_counters.save()

        try:
            user_feeds = dj_user.user_feeds

        except:
            user_feeds = UserFeeds(user=dj_user)
            user_feeds.save()

        user_feeds.check()

        try:
            user_subscriptions = dj_user.user_subscriptions

        except:
            user_subscriptions = UserSubscriptions(user=dj_user)
            user_subscriptions.save()

        user_subscriptions.check()

    created_users_count = \
        User.objects.all().count() - current_users_count

    created_internal_feeds_count = \
        UserFeeds.objects.all().count() - internal_feeds_count

    LOGGER.info(u'{0} users checked, {1} created, and {2} internal '
                u'feeds created.'.format(
                    all_users_count,
                    created_users_count,
                    created_internal_feeds_count))


def migrate_all_folders(stop_on_exception=True, verbose=False):
    """ Migrate things. """

    LOGGER.info(u'Starting to migrate folders at %s…', now())

    mongo_folders = not_yet_migrated(all_folders)
    mongo_folders_count = mongo_folders.count()

    for mongo_folder in mongo_folders:

        try:
            folder, created = migrate_folder(mongo_folder)

        except:
            LOGGER.exception(u'Could not migrate folder %s', mongo_folder.id)

            if stop_on_exception:
                raise StopMigration('folder')

            else:
                continue

        else:
            if verbose:
                LOGGER.info(u'Migrated folder %s → %s', mongo_folder, folder)

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_folder.update(set__bigmig_migrated=True)

        if created:
            counters.created_folders_count += 1

        counters.migrated_folders_count += 1

        if counters.migrated_folders_count % 50 == 0:
            vacuum_analyze(u'(at {0} folders)'.format(
                counters.migrated_folders_count))

    LOGGER.info(u'Folders migrated: {0}/{1} (total {2}), '
                u'{3} already there.'.format(
                    counters.migrated_folders_count,
                    mongo_folders_count,
                    all_folders_count,
                    counters.migrated_folders_count
                    - counters.created_folders_count))


def migrate_all_subscriptions(stop_on_exception=True, verbose=False):
    """ Migrate things. """

    LOGGER.info(u'Starting to migrate subscriptions at %s…', now())

    mongo_subscriptions = not_yet_migrated(all_subscriptions)
    mongo_subscriptions_count = mongo_subscriptions.count()

    for mongo_subscription in mongo_subscriptions:

        try:
            subscription, created = migrate_subscription(mongo_subscription)

        except:
            LOGGER.exception(u'Could not migrate subscription %s',
                             mongo_subscription.id)

            if stop_on_exception:
                raise StopMigration('subscription')

            else:
                continue

        else:
            if verbose:
                LOGGER.info(u'Migrated subscription %s → %s',
                            mongo_subscription, subscription)

        if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
            # Avoid a full save() cycle, we don't need it anyway.
            mongo_subscription.update(set__bigmig_migrated=True)

        if created:
            counters.created_subscriptions_count += 1

        counters.migrated_subscriptions_count += 1

        if counters.migrated_subscriptions_count % 500 == 0:
            vacuum_analyze(u'(at {0} subscriptions)'.format(
                counters.migrated_subscriptions_count))

    LOGGER.info(u'Subscriptions migrated: {0}/{1} (total {2}), '
                u'{3} already there.'.format(
                    counters.migrated_subscriptions_count,
                    mongo_subscriptions_count,
                    all_subscriptions_count,
                    counters.migrated_subscriptions_count
                    - counters.created_subscriptions_count))


def migrate_all_articles(stop_on_exception=True, verbose=False):
    """ Migrate articles. """

    LOGGER.info(u'Starting to migrate articles at %s…', now())

    raise NotImplementedError('DEAL WITH ORPHANED PROBLEM.')

    # ————————————————————————————————————————————————————————————— masters

    master_articles = master_documents(all_articles)
    master_articles_count = master_articles.count()

    migrate_articles(master_articles,
                     stop_on_exception=stop_on_exception,
                     verbose=verbose)

    # —————————————————————————————————————————————————————————— duplicates

    duplicate_articles = all_articles.filter(duplicate_of__ne=None)
    duplicate_articles_count = duplicate_articles.count()

    migrate_articles(duplicate_articles,
                     stop_on_exception=stop_on_exception,
                     verbose=verbose)

    LOGGER.info(u'Articles migrated: %s/%s (total %s), '
                u'%s dupes, %s already there.',
                counters.migrated_articles_count,
                master_articles_count,
                all_articles_count,
                duplicate_articles_count,
                counters.migrated_articles_count
                - counters.created_articles_count)


def migrate_all_reads(stop_on_exception=True, verbose=False):
    """ Migrate remaining reads.

    There should be none, as article should have migrated all of them.
    Thus, it's just a check.
    """

    LOGGER.info(u'Starting to migrate reads at %s…', now())

    mongo_reads = not_yet_migrated(all_reads)
    mongo_reads_count = mongo_reads.count()

    migrate_reads(mongo_reads,
                  stop_on_exception=stop_on_exception,
                  verbose=verbose)

    LOGGER.info(u'Reads migrated: %s/%s (total %s), '
                u'%s already there.',
                counters.migrated_reads_count,
                mongo_reads_count,
                all_reads_count,
                counters.migrated_reads_count
                - counters.created_reads_count)


def migrate_all_tags(stop_on_exception=True, verbose=False):
    """ Migrate things. """

    LOGGER.info(u'Starting to migrate tags at %s…', now())

    # ————————————————————————————————————————————————————————————— masters

    master_tags = master_documents(all_tags)

    master_tags_count = master_tags.count()

    migrate_tags(master_tags,
                 stop_on_exception=stop_on_exception,
                 verbose=verbose)

    # —————————————————————————————————————————————————————————— duplicates

    duplicate_tags = all_tags.filter(MQ(duplicate_of__ne=None))
    duplicate_tags_count = duplicate_tags.count()

    migrate_tags(duplicate_tags,
                 stop_on_exception=stop_on_exception,
                 verbose=verbose)

    LOGGER.info(u'Tags migrated: %s/%s (total %s), '
                u'%s dupes, %s already there.',
                counters.migrated_tags_count,
                master_tags_count,
                all_tags_count,
                duplicate_tags_count,
                counters.migrated_tags_count
                - counters.created_tags_count)


def reassign_all_tags(stop_on_exception=True, verbose=False):
    """ Re-assign all tags global task. """

    LOGGER.info(u'Starting to re-assign all tags at %s…', now())

    with benchmark('Re-assign tags on feeds'):
        reassign_tags_on_feeds(stop_on_exception=stop_on_exception,
                               verbose=verbose)

    with benchmark('Re-assign tags on subscriptions'):
        reassign_tags_on_subscriptions(stop_on_exception=stop_on_exception,
                                       verbose=verbose)

    with benchmark('Re-assign tags on articles'):
        reassign_tags_on_articles(stop_on_exception=stop_on_exception,
                                  verbose=verbose)

    with benchmark('Re-assign tags on reads'):
        reassign_tags_on_reads(stop_on_exception=stop_on_exception,
                               verbose=verbose)

    total_impacted_objects = \
        counters.reassigned_objects_count + counters.failed_objects_count

    LOGGER.info(u'Successfully reassigned %s tags on %s objects '
                u'of a %s total, %s reassignation failed.',
                counters.reassigned_tags_count,
                counters.reassigned_objects_count,
                total_impacted_objects,
                counters.failed_objects_count
                )


# ————————————————————————————————————————————————————————————————— Global task


@task(queue='background')
def migrate_all_mongo_data(force=False, stop_on_exception=True, verbose=False):
    """ Copy and refresh all mongodb data into PostgreSQL. """

    if config.CHECK_DATABASE_MIGRATION_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'Database migration disabled in configuration.')
        return

    # One week for a migration should be OK.
    my_lock = RedisExpiringLock('migrate_all_data', expire_time=604800)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'Forcing database migration…')

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'migrate_all_mongo_data() is already '
                           u'locked, aborting.')
            return

    LOGGER.info(u'Starting to migrate everything at %s…', now())

    with benchmark('migrate_all_mongo_data()'):
        try:
            with benchmark(u'Migrate users & preferences'):
                migrate_all_users_and_preferences(
                    stop_on_exception=stop_on_exception, verbose=verbose)

            with benchmark(u'Migrate Web sites'):
                migrate_all_websites(stop_on_exception=stop_on_exception,
                                     verbose=verbose)

            with benchmark(u'Migrate Authors'):
                migrate_all_authors(stop_on_exception=stop_on_exception,
                                    verbose=verbose)

            with benchmark(u'Migrate RSS/Atom feeds'):
                migrate_all_feeds(stop_on_exception=stop_on_exception,
                                  verbose=verbose)

            with benchmark(u'Check internal feeds / subscriptions'):
                check_internal_users_feeds_and_subscriptions(
                    stop_on_exception=stop_on_exception, verbose=verbose)

            # Subscriptions need their folders.
            with benchmark(u'Migrate all folders'):
                migrate_all_folders(stop_on_exception=stop_on_exception,
                                    verbose=verbose)

            with benchmark(u'Migrate all subscriptions'):
                migrate_all_subscriptions(stop_on_exception=stop_on_exception,
                                          verbose=verbose)

            with benchmark(u'Migrate all articles'):
                migrate_all_articles(stop_on_exception=stop_on_exception,
                                     verbose=verbose)

            with benchmark(u'Migrate all reads'):
                migrate_all_reads(stop_on_exception=stop_on_exception,
                                  verbose=verbose)

            # Now that all tag origins are created, we can copy all of them
            # and reassign them to feeds / articles / subscriptions / reads.
            with benchmark(u'Migrate all tags'):
                migrate_all_tags(stop_on_exception=stop_on_exception,
                                 verbose=verbose)

            with benchmark(u'Re-assign tags'):
                reassign_all_tags(stop_on_exception=stop_on_exception,
                                  verbose=verbose)

            # for each feed
            # copy subscriptions
            # migrate each article

            # this should check reads

        finally:
            my_lock.release()

        LOGGER.info(u'Migration finished. Enjoy your shining PG database.')
