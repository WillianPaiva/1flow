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
import logging

from constance import config

from celery import task

from inspect_model import InspectModel

from mongoengine import Q as MQ

# from django.db.models import Q
from django.db import connection
# from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.dateutils import benchmark

from ..models.common import (
    USER_FEEDS_SITE_URL,
)

from ..models.reldb import (
    User, Preferences,
    SimpleTag as Tag,
    WebSite,
    Author,

    BaseFeed, RssAtomFeed,
    Article, OriginalData,
    Subscription,
    Read,

    Folder,

    UserFeeds, UserSubscriptions,
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

MONGO_INTERNAL_FEED_URL_RE = re.compile(
    USER_FEEDS_SITE_URL.replace(u'{user.id}', ur'(?P<uid>\w{24,24})'))


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

def get_article_from_mongo_article(mongo_article):
    """ Find an article in PG from one in MongoDB. """

    return Article.objects.get(mongo_article.url)


def get_read_from_mongo_read(mongo_read):
    """ Find a read in PG from one in MongoDB. """

    return Read.objects.get(
        item=get_article_from_mongo_article(mongo_read.article),
        user=mongo_read.user.django,
    )


def get_folder_from_mongo_folder(mongo_folder):
    """ Get the PG equivalent of a mongodb folder. """

    return Folder.objects.get(
        name=mongo_folder.name,
        user=mongo_folder.owner.django,
        parent=None if mongo_folder.parent is None
        else get_folder_from_mongo_folder(mongo_folder.parent)
    )


def get_feed_from_mongo_feed(mongo_feed):
    """ Return the PG equivalent of a mongoDB feed, internal or not. """

    if mongo_feed.is_internal:
        return get_internal_feed_from_mongo_feed(mongo_feed)

    else:
        return BaseFeed.objects.get(url=mongo_feed.url)


def get_internal_feed_from_mongo_feed(mongo_feed):
    """ Get the PostgreSQL equivalent of a MongoEngine internal feed. """

    match = MONGO_INTERNAL_FEED_URL_RE.match(mongo_feed.url)

    if match is not None:
        uid = match.group('uid')
        user = MongoUser.objects.get(id=uid)

    else:
        return None

    # This is probably not the best way of
    # finding which feed it is, but it works:

    if mongo_feed == user.web_import_feed:
        return user.django.user_feeds.imported_items

    if mongo_feed == user.sent_items_feed:
        return user.django.user_feeds.sent_items

    if mongo_feed == user.received_items:
        return user.django.user_feeds.received_items

    # NOTE: there are no `written_items` in the MongoDB database.

    return None


def get_subscription_from_mongo_subscription(mongo_subscription):
    """ Return the PG equivalent of a mongoDB subscription, internal or not. """

    return Subscription.objects.get(
        user=mongo_subscription.user.django,
        feed=get_feed_from_mongo_feed(mongo_subscription.feed)
    )


# —————————————————————————————————————————————————————————————— Migrate models


def migrate_user_and_preferences(mongo_user):
    """  Migrate a user and his/her preferences from mongdb to PG. """

    # Should create it if not already done.
    user = mongo_user.django

    # If already existing, preferences could have not been created yet.
    try:
        user.preferences

    except Preferences.DoesNotExist:
        preferences = Preferences(user=user)
        preferences.save()
        preferences.check()

    user.save()

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
        name=mongo_website.name,
        slug=mongo_website.slug,
        url=mongo_website.url,
        is_restricted=mongo_website.restricted,
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
        return Author.objects.get(
            origin_name=mongo_author.origin_name,
            website=WebSite.objects.get(url=mongo_author.website.url)), False

    except Author.DoesNotExist:
        pass

    author = Author(
        name=mongo_author.name,
        origin_name=mongo_author.origin_name,
        website=WebSite.objects.get(url=mongo_author.website.url),
        url=mongo_author.url,
        is_unsure=mongo_author.is_unsure,
    )

    # We assume the master is already created.
    # See the master migration task for details.
    if mongo_author.duplicate_of:
        author.duplicate_of = Author.objects.get(
            url=mongo_author.duplicate_of.url)

    if mongo_author.user:
        author.user = mongo_author.user.django

    author.save()

    return author, True


def migrate_feed(mongo_feed):
    """  Migrate a non-internal feed from mongdb to PG. """

    try:
        return get_feed_from_mongo_feed(url=mongo_feed.url), False

    except RssAtomFeed.DoesNotExist:
        pass

    feed = RssAtomFeed(
        name=mongo_feed.name,
        slug=mongo_feed.slug,
        url=mongo_feed.url,
        is_restricted=mongo_feed.restricted,

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
        feed.duplicate_of = get_feed_from_mongo_feed(
            url=mongo_feed.duplicate_of.url)

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

    return feed, True


def migrate_article(mongo_article):
    """ Migrate a MongoDB article into PostgreSQL. """

    try:
        article = get_article_from_mongo_article(mongo_article)

    except Article.DoesNotExist:
        article = Article(

            # BaseItem
            name=mongo_article.title,

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

    # UrlItem
    # article.url is already set at creation
    article.is_orphaned = mongo_article.orphaned
    article.url_absolute = mongo_article.url_absolute
    article.url_error = mongo_article.url_error

    # ContentItem
    article.image_url = mongo_article.image_url
    article.excerpt = mongo_article.excerpt
    article.content = mongo_article.content
    article.content_type = mongo_article.content_type
    article.content_error = mongo_article.content_error

    # Needed for ManyToManyField() to succeed.
    article.save()

    needs_save = False

    if mongo_article.duplicate_of:
        article.duplicate_of = get_article_from_mongo_article(
            mongo_article.duplicate_of)
        needs_save = True

    if mongo_article.created_by:
        article.user = mongo_article.created_by.django
        needs_save = True

    if mongo_article.authors:
        authors = []

        for mongo_author in mongo_article.authors:
            authors.append(Author.objects.get(
                origin_name=mongo_author.origin_name,
                website=WebSite.objects.get(url=mongo_author.website.url)))

        article.authors.add(*authors)

    if mongo_article.source:
        try:
            Article.sources.add(
                get_article_from_mongo_article(mongo_article.source)
            )
            needs_save = True

        except:
            LOGGER.exception(u'Could not reassign source on article %s',
                             article)

    feeds = []

    for mongo_feed in mongo_article.feeds:
        feeds.append(get_feed_from_mongo_feed(mongo_feed))

    if feeds:
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

    return article, True


def migrate_folder(mongo_folder):
    """ Migrate a Folder from MongoDB to PostgreSQL. """

    #
    # HEADS UP: we always try to get_or_create(), because our current
    #           PG DB can already have the folder even if not migrated.
    #
    if mongo_folder.parent:
        parent, created = migrate_folder(mongo_folder.parent)
    else:
        parent = None

    if mongo_folder.children:
        children = []

        for mongo_child in mongo_folder.children:
            child, created = migrate_folder(mongo_folder.parent)
            children.append(child)

    else:
        children = None

    return Folder.add_folder(
        name=mongo_folder.name,
        user=mongo_folder.owner.django,
        parent=parent,
        children=children,
    )


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
        if read.date_created <= mongo_read.date_added:
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
        tag.language = Language.get_by_code(mongo_tag.language)

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

    return tag, created


# ——————————————————————————————————————————————————————————————— Reassign tags


def reassign_tags_on_feed(mongo_feed):
    """ Set the same tags on a PG feed that are on a mongo one. """

    feed = get_feed_from_mongo_feed(mongo_feed)

    tags = Tag.get_tags_set(tuple(t.name for t in mongo_feed.tags))

    feed.tags.add(*tags)

    return tags.count()


def reassign_tags_on_subscription(mongo_subscription):
    """ Set the same tags on a PG subscription that are on a mongo one. """

    subscription = get_subscription_from_mongo_subscription(mongo_subscription)

    tags = Tag.get_tags_set(tuple(t.name for t in mongo_subscription.tags))

    subscription.tags.add(*tags)

    return tags.count()


def reassign_tags_on_article(mongo_article):
    """ Set the same tags on a PG article that are on a mongo one. """

    article = get_article_from_mongo_article(url=mongo_article.url)

    tags = Tag.get_tags_set(tuple(t.name for t in mongo_article.tags))

    article.tags.add(*tags)

    return tags.count()


def reassign_tags_on_read(mongo_read):
    """ Set the same tags on a PG read that are on a mongo one. """

    read = get_read_from_mongo_read(mongo_read)

    tags = Tag.get_tags_set(tuple(t.name for t in mongo_read.tags))

    read.tags.add(*tags)

    return tags.count()


# ————————————————————————————————————————————————————————————————— Global task


class StopMigration(Exception):

    """ Raised when the migration must stop immediately. """

    pass


@task(queue='background')
def migrate_all_mongo_data(force=False, stop_on_exception=True):
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
            LOGGER.warning(_(u'Forcing database migration…'))

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'migrate_all_mongo_data() is already '
                           u'locked, aborting.')
            return

    all_websites = MongoWebSite.objects.all().no_cache()
    all_websites_count = all_websites.count()
    created_websites_count = 0
    migrated_websites_count = 0

    all_authors = MongoAuthor.objects.all().no_cache()
    all_authors_count = all_authors.count()
    created_authors_count = 0
    migrated_authors_count = 0

    all_users = MongoUser.objects.all().no_cache()
    all_users_count = all_users.count()
    # created_users_count = 0  # useless because we can't know
    migrated_users_count = 0

    all_feeds = MongoFeed.objects.all().no_cache()
    all_feeds_count = all_feeds
    created_feeds_count = 0
    migrated_feeds_count = 0

    all_tags = MongoTag.objects.all().no_cache()
    all_tags_count = all_tags.count()
    created_tags_count = 0
    migrated_tags_count = 0

    all_articles = MongoArticle.objects.all().no_cache()
    all_articles_count = all_articles.count()
    created_articles_count = 0
    migrated_articles_count = 0

    all_folders = MongoFolder.objects.all().no_cache()
    all_folders_count = all_folders.count()
    created_folders_count = 0
    migrated_folders_count = 0

    all_subscriptions = MongoSubscription.objects.all().no_cache()
    all_subscriptions_count = all_subscriptions.count()
    created_subscriptions_count = 0
    migrated_subscriptions_count = 0

    all_reads = MongoRead.objects.all().no_cache()
    all_reads_count = all_reads.count()
    created_reads_count = 0
    migrated_reads_count = 0

    # ———————————————————————————————————————————————— Models groups migrations

    # NOT NEEDED: def migrate_users_and_preferences(users):

    def migrate_websites(websites):

        global created_websites_count, migrated_websites_count

        for mongo_website in not_yet_migrated(websites):
            try:
                website, created = migrate_website(mongo_website)

            except:
                LOGGER.exception(u'Could not migrate website %s',
                                 mongo_website)

                if stop_on_exception:
                    raise StopMigration('website')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_website.update(set__bigmig_migrated=True)

            if created:
                created_websites_count += 1

            migrated_websites_count += 1

            if migrated_websites_count % 500 == 0:
                vacuum_analyze(u'(at {0} websites)'.format(
                    migrated_websites_count))

    def migrate_authors(authors):

        global created_authors_count, migrated_authors_count

        for mongo_author in not_yet_migrated(authors):
            try:
                author, created = migrate_author(mongo_author)

            except:
                LOGGER.exception(u'Could not migrate author %s',
                                 mongo_author)

                if stop_on_exception:
                    raise StopMigration('author')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_author.update(set__bigmig_migrated=True)

            if created:
                created_authors_count += 1

            migrated_authors_count += 1

            if migrated_authors_count % 500 == 0:
                vacuum_analyze(u'(at {0} authors)'.format(
                    migrated_authors_count))

    def migrate_feeds(feeds):

        global created_feeds_count, migrated_feeds_count

        for mongo_feed in not_yet_migrated(feeds):
            try:
                feed, created = migrate_feed(mongo_feed)

            except:
                LOGGER.exception(u'Could not migrate feed %s', mongo_feed)

                if stop_on_exception:
                    raise StopMigration('feed')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_feed.update(set__bigmig_migrated=True)

            if created:
                created_feeds_count += 1

            migrated_feeds_count += 1

            if migrated_feeds_count % 500 == 0:
                vacuum_analyze(u'(at {0} feeds)'.format(migrated_feeds_count))

    # NOT NEEDED: def migrate_folders(folders):

    # NOT NEEDED: def migrate_subscriptions(subscriptions):

    # NOT NEEDED: def migrate_reads(reads):

    def migrate_tags(tags):

        global created_tags_count, migrated_tags_count

        for mongo_tag in not_yet_migrated(tags):
            try:
                tag, created = migrate_tag(mongo_tag)

            except:
                LOGGER.exception(u'Could not migrate tag %s', mongo_tag)

                if stop_on_exception:
                    raise StopMigration('tag')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_tag.update(set__bigmig_migrated=True)

            if created:
                created_tags_count += 1

            migrated_tags_count += 1

            if migrated_tags_count % 10000 == 0:
                vacuum_analyze(u'(at {0} tags)'.format(migrated_tags_count))

    def migrate_articles(articles):

        global created_articles_count, migrated_articles_count

        for mongo_article in not_yet_migrated(articles):
            try:
                article, created = migrate_article(mongo_article)

            except:
                LOGGER.exception(u'Could not migrate article %s', mongo_article)

                if stop_on_exception:
                    raise StopMigration('article')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_article.update(set__bigmig_migrated=True)

            if created:
                created_articles_count += 1

            migrated_articles_count += 1

            if migrated_articles_count % 10000 == 0:
                vacuum_analyze(u'(at {0} tags)'.format(migrated_articles_count))

    # ——————————————————————————————————————————————————————— Models migrations

    def migrate_all_users_and_preferences():

        global migrated_users_count

        for mongo_user in not_yet_migrated(MongoUser.objects.all()):

            try:
                user, created = migrate_user_and_preferences(mongo_user)

            except:
                LOGGER.exception(u'Could not migrate user %s',
                                 mongo_user)

                if stop_on_exception:
                    raise StopMigration('user')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_user.update(set__bigmig_migrated=True)

            migrated_users_count += 1

            if migrated_users_count % 25 == 0:
                vacuum_analyze(u'(at {0} users)'.format(
                    migrated_users_count))

        LOGGER.info(u'Users migrated: {0}/{1}.'.format(
                    migrated_users_count,
                    all_users_count,
                    ))

    def migrate_all_websites():

        masters_websites = master_documents(all_websites)
        # masters_websites_count = masters_websites.count()

        migrate_websites(masters_websites)

        duplicates_websites = all_websites.filter(duplicate_of__ne=None)
        duplicates_websites_count = duplicates_websites.count()

        migrate_websites(duplicates_websites)

        LOGGER.info(u'Web sites migrated: {0}/{1}, '
                    u' {2} dupes, {3} already there.'.format(
                        migrated_websites_count,
                        all_websites_count,
                        duplicates_websites_count,
                        migrated_websites_count - created_websites_count
                    ))

    def migrate_all_authors():

        masters_authors = master_documents(all_authors)
        # masters_authors_count = masters_authors.count()

        migrate_authors(masters_authors)

        duplicates_authors = all_authors.filter(duplicate_of__ne=None)
        duplicates_authors_count = duplicates_authors.count()

        migrate_authors(duplicates_authors)

        LOGGER.info(u'Authors migrated: {0}/{1}, '
                    u' {2} dupes, {3} already there.'.format(
                        migrated_authors_count,
                        all_authors_count,
                        duplicates_authors_count,
                        migrated_authors_count - created_authors_count
                    ))

    def migrate_all_feeds():

        external_feeds = all_feeds.filter(is_internal=False)
        external_feeds_count = external_feeds.count()

        # ————————————————————————————————————————————————————————————— masters

        master_external = master_documents(external_feeds)

        migrate_feeds(master_external)

        # —————————————————————————————————————————————————————————— duplicates

        duplicates_external = external_feeds.filter(duplicate_of__ne=None)
        duplicates_external_count = duplicates_external.count()

        migrate_feeds(duplicates_external)

        # ————————————————————————————————————————————————————————————————— end

        LOGGER.info(u'RSS/Atom feeds migrated: {0}/{1} (total {2}), '
                    u' {3} dupes, {4} already there.'.format(
                        migrated_feeds_count,
                        external_feeds_count,
                        all_feeds_count,
                        duplicates_external_count,
                        migrated_feeds_count - created_feeds_count
                    ))

    def check_internal_users_feeds_and_subscriptions():
        """ Create internal feeds and subscriptions for all users. """

        global created_users_count

        current_users_count = User.objects.all().count()
        internal_feeds_count = UserFeeds.objects.all().count()

        for mongo_user in all_users:
            dj_user = mongo_user.django

            try:
                dj_user.user_feeds

            except:
                user_feeds = UserFeeds(user=dj_user)
                user_feeds.save()

            try:
                dj_user.user_subscriptions

            except:
                user_subscriptions = UserSubscriptions(user=dj_user)
                user_subscriptions.save()

        created_users_count = \
            User.objects.all().count() - current_users_count

        created_internal_feeds_count = \
            UserFeeds.objects.all().count() - internal_feeds_count

        LOGGER.info(u'%s users checked, %s created, and %s internal '
                    u'feeds created.',
                    all_users_count,
                    created_users_count,
                    created_internal_feeds_count)

    def migrate_all_articles():

        # ————————————————————————————————————————————————————————————— masters

        master_articles = master_documents(all_articles)
        master_articles_count = master_articles.count()

        migrate_articles(master_articles)

        # —————————————————————————————————————————————————————————— duplicates

        duplicate_articles = all_articles.filter(duplicate_of__ne=None)
        duplicate_articles_count = duplicate_articles.count()

        migrate_articles(duplicate_articles)

        LOGGER.info(u'Articles migrated: {0}/{1} (total {2}), '
                    u' {3} dupes, {4} already there.'.format(
                        migrated_articles_count,
                        master_articles_count,
                        all_articles_count,
                        duplicate_articles_count,
                        migrated_articles_count - created_articles_count
                    ))

    def migrate_all_folders():

        # ————————————————————————————————————————————————————————————— masters

        global created_folders_count, migrated_folders_count

        mongo_folders = not_yet_migrated(all_folders)
        mongo_folders_count = mongo_folders.count()

        for mongo_folder in mongo_folders:

            try:
                folder, created = migrate_folder(mongo_folder)

            except:
                LOGGER.exception(u'Could not migrate folder %s',
                                 mongo_folder)

                if stop_on_exception:
                    raise StopMigration('folder')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_folder.update(set__bigmig_migrated=True)

            if created:
                created_folders_count += 1

            migrated_folders_count += 1

            if migrated_folders_count % 50 == 0:
                vacuum_analyze(u'(at {0} folders)'.format(
                    migrated_folders_count))

        # ————————————————————————————————————————————————————————————————— end

        LOGGER.info(u'Folders migrated: {0}/{1} (total {2}), '
                    u'{3} already there.'.format(
                        migrated_folders_count,
                        mongo_folders_count,
                        all_folders_count,
                        migrated_folders_count
                        - created_folders_count
                    ))

    def migrate_all_subscriptions():

        # ————————————————————————————————————————————————————————————— masters

        global created_subscriptions_count, migrated_subscriptions_count

        mongo_subscriptions = not_yet_migrated(all_subscriptions)
        mongo_subscriptions_count = mongo_subscriptions.count()

        for mongo_subscription in mongo_subscriptions:

            try:
                subscription, created = migrate_subscription(mongo_subscription)

            except:
                LOGGER.exception(u'Could not migrate subscription %s',
                                 mongo_subscription)

                if stop_on_exception:
                    raise StopMigration('subscription')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_subscription.update(set__bigmig_migrated=True)

            if created:
                created_subscriptions_count += 1

            migrated_subscriptions_count += 1

            if migrated_subscriptions_count % 500 == 0:
                vacuum_analyze(u'(at {0} subscriptions)'.format(
                    migrated_subscriptions_count))

        # ————————————————————————————————————————————————————————————————— end

        LOGGER.info(u'Subscriptions migrated: {0}/{1} (total {2}), '
                    u' {3} already there.'.format(
                        migrated_subscriptions_count,
                        mongo_subscriptions_count,
                        all_subscriptions_count,
                        migrated_subscriptions_count
                        - created_subscriptions_count
                    ))

    def migrate_all_reads():

        # ————————————————————————————————————————————————————————————— masters

        global created_reads_count, migrated_reads_count

        mongo_reads = not_yet_migrated(all_reads)
        mongo_reads_count = mongo_reads.count()

        for mongo_read in mongo_reads:

            try:
                read, created = migrate_read(mongo_read)

            except:
                LOGGER.exception(u'Could not migrate read %s',
                                 mongo_read)

                if stop_on_exception:
                    raise StopMigration('read')

                else:
                    continue

            if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                # Avoid a full save() cycle, we don't need it anyway.
                mongo_read.update(set__bigmig_migrated=True)

            if created:
                created_reads_count += 1

            migrated_reads_count += 1

            if migrated_reads_count % 100000 == 0:
                vacuum_analyze(u'(at {0} reads)'.format(
                    migrated_reads_count))

        # ————————————————————————————————————————————————————————————————— end

        LOGGER.info(u'Reads migrated: {0}/{1} (total {2}), '
                    u' {3} already there.'.format(
                        migrated_reads_count,
                        mongo_reads_count,
                        all_reads_count,
                        migrated_reads_count
                        - created_reads_count
                    ))

    def migrate_all_tags():

        global created_tags_count, migrated_tags_count

        # ————————————————————————————————————————————————————————————— masters

        master_tags = MongoTag.objects.filter(MQ(duplicate_of__exist=False)
                                              | MQ(duplicate_of=None))

        master_tags_count = master_tags.count()

        migrate_tags(master_tags)

        # —————————————————————————————————————————————————————————— duplicates

        duplicate_tags = MongoTag.objects.filter(MQ(duplicate_of__ne=None))
        duplicate_tags_count = duplicate_tags.count()

        migrate_tags(duplicate_tags)

        LOGGER.info(u'Tags migrated: {0}/{1} (total {2}), '
                    u' {3} dupes, {4} already there.'.format(
                        migrated_tags_count,
                        master_tags_count,
                        all_tags_count,
                        duplicate_tags_count,
                        migrated_tags_count - created_tags_count
                    ))

    def reassign_all_tags():

        reassigned_objects_count = 0
        reassigned_tags_count = 0
        failed_objects_count = 0

        def reassign_tags_on_feeds():

            global reassigned_objects_count
            global reassigned_tags_count
            global failed_objects_count

            LOGGER.info(u'Starting to reassign tags on feeds. '
                        u'This will take a while…')

            for feed in no_tags_reassigned(all_feeds):
                try:
                    reassigned_tags_count += reassign_tags_on_feed(feed)
                    reassigned_objects_count += 1

                except:
                    failed_objects_count += 1
                    LOGGER.exception(u'Could not reassign tags on feed %s',
                                     feed)

                    if stop_on_exception:
                        raise StopMigration('reassign tags on feed')

                    else:
                        continue

                if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                    # Avoid a full save() cycle, we don't need it anyway.
                    feed.update(set__bigmig_reassigned=True)

        def reassign_tags_on_subscriptions():

            global reassigned_objects_count
            global reassigned_tags_count
            global failed_objects_count

            LOGGER.info(u'Starting to reassign tags on subscriptions. '
                        u'This will take a while…')

            for subscription in no_tags_reassigned(all_subscriptions):
                try:
                    reassigned_tags_count += \
                        reassign_tags_on_subscription(subscription)
                    reassigned_objects_count += 1

                except:
                    failed_objects_count += 1
                    LOGGER.exception(u'Could not reassign tags on '
                                     u'subscription %s', subscription)

                    if stop_on_exception:
                        raise StopMigration('reassign tags on subscription')

                    else:
                        continue

                if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                    # Avoid a full save() cycle, we don't need it anyway.
                    subscription.update(set__bigmig_reassigned=True)

        def reassign_tags_on_articles():

            global reassigned_objects_count
            global reassigned_tags_count
            global failed_objects_count

            LOGGER.info(u'Starting to reassign tags on articles. '
                        u'This will take a while…')

            for article in no_tags_reassigned(all_articles):
                try:
                    reassigned_tags_count += reassign_tags_on_article(article)
                    reassigned_objects_count += 1

                except:
                    failed_objects_count += 1
                    LOGGER.exception(u'Could not reassign tags on article %s',
                                     article)

                    if stop_on_exception:
                        raise StopMigration('reassign tags on article')

                    else:
                        continue

                if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                    # Avoid a full save() cycle, we don't need it anyway.
                    article.update(set__bigmig_reassigned=True)

        def reassign_tags_on_reads():

            global reassigned_objects_count
            global reassigned_tags_count
            global failed_objects_count

            LOGGER.info(u'Starting to reassign tags on reads. '
                        u'This will take a while…')

            for read in no_tags_reassigned(all_reads):
                try:
                    reassigned_tags_count += reassign_tags_on_read(read)
                    reassigned_objects_count += 1

                except:
                    failed_objects_count += 1
                    LOGGER.exception(u'Could not reassign tags on read %s',
                                     read)

                    if stop_on_exception:
                        raise StopMigration('reassign tags on read')

                    else:
                        continue

                if config.CHECK_DATABASE_MIGRATION_DEFINIVE_RUN:
                    # Avoid a full save() cycle, we don't need it anyway.
                    read.update(set__bigmig_reassigned=True)

        with benchmark('Re-assign tags on feeds'):
            reassign_tags_on_feeds()

        with benchmark('Re-assign tags on subscriptions'):
            reassign_tags_on_subscriptions()

        with benchmark('Re-assign tags on articles'):
            reassign_tags_on_articles()

        with benchmark('Re-assign tags on reads'):
            reassign_tags_on_reads()

        total_impacted_objects = reassigned_objects_count + failed_objects_count

        LOGGER.info(u'Successfully reassigned %s tags on %s objects '
                    u'of a %s total, %s reassignation failed.',
                    reassigned_tags_count, reassigned_objects_count,
                    total_impacted_objects,
                    failed_objects_count
                    )

    # ————————————————————————————————————————————————————————— The global task

    with benchmark('migrate_all_mongo_data()'):
        try:
            with benchmark(u'Migrate users & preferences'):
                migrate_all_users_and_preferences()

            with benchmark(u'Migrate Web sites'):
                migrate_all_websites()

            with benchmark(u'Migrate Authors'):
                migrate_all_authors()

            with benchmark(u'Migrate RSS/Atom feeds'):
                migrate_all_feeds()

            with benchmark(u'Check internal feeds / subscriptions'):
                check_internal_users_feeds_and_subscriptions()

            with benchmark(u'Migrate all articles'):
                migrate_all_articles()

            # Subscriptions need their folders.
            with benchmark(u'Migrate all folders'):
                migrate_all_folders()

            with benchmark(u'Migrate all subscriptions'):
                migrate_all_subscriptions()

            with benchmark(u'Migrate all reads'):
                migrate_all_reads()

            # Now that all tag origins are created, we can copy all of them
            # and reassign them to feeds / articles / subscriptions / reads.
            with benchmark(u'Migrate all tags'):
                migrate_all_tags()

            with benchmark(u'Re-assign tags'):
                reassign_all_tags()

            # for each feed
            # copy subscriptions
            # migrate each article

            # this should check reads

        finally:
            my_lock.release()

        LOGGER.info(u'Migration finished. Enjoy your shining PG database.')
