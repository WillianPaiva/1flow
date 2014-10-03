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

import logging

from constance import config

from pymongo.errors import DuplicateKeyError
from mongoengine.errors import NotUniqueError, ValidationError
from mongoengine.context_managers import no_dereference

from celery import task

from ..models import Article
from ..stats import synchronize_statsd_articles_gauges

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.dateutils import (now, timedelta, benchmark)

LOGGER = logging.getLogger(__name__)


def archive_article_one_internal(article, counts):
    """ Internal function.

    Do not use directly unless you know what you're doing.
    """

    delete_anyway = True
    article.switch_db('archive')

    try:
        article.save()

    except (NotUniqueError, DuplicateKeyError):
        counts['archived_dupes'] += 1

    except ValidationError:
        # If the article doesn't validate in the archive database, how
        # the hell did it make its way into the production one?? Perhaps
        # a scoria of the GR import which did update_one(set_*…), which
        # bypassed the validation phase.
        # Anyway, beiing here means the article is duplicate or orphaned.
        # So just forget the validation error and wipe it from production.
        LOGGER.exception(u'Article archiving failed for %s', article)
        counts['bad_articles'] += 1

    except:
        delete_anyway = False

    if delete_anyway:
        article.switch_db('default')
        article.delete()


@task(queue='clean')
def archive_articles(limit=None):
    """ Archive articles that pollute the production database. """

    counts = {
        'duplicates': 0,
        'orphaned': 0,
        'bad_articles': 0,
        'archived_dupes': 0,
    }

    if limit is None:
        limit = config.ARTICLE_ARCHIVE_BATCH_SIZE

    with no_dereference(Article) as ArticleOnly:
        if config.ARTICLE_ARCHIVE_OLDER_THAN > 0:
            older_than = now() - timedelta(
                days=config.ARTICLE_ARCHIVE_OLDER_THAN)

            duplicates = ArticleOnly.objects(
                duplicate_of__ne=None,
                date_published__lt=older_than).limit(limit)
            orphaned   = ArticleOnly.objects(
                orphaned=True,
                date_published__lt=older_than).limit(limit)

        else:
            duplicates = ArticleOnly.objects(duplicate_of__ne=None
                                             ).limit(limit)
            orphaned   = ArticleOnly.objects(orphaned=True).limit(limit)

    duplicates.no_cache()
    orphaned.no_cache()

    counts['duplicates'] = duplicates.count()
    counts['orphaned']   = orphaned.count()

    if counts['duplicates']:
        current = 0
        LOGGER.info(u'Archiving of %s duplicate article(s) started.',
                    counts['duplicates'])

        with benchmark('Archiving of %s duplicate article(s)'
                       % counts['duplicates']):
            for article in duplicates:
                archive_article_one_internal(article, counts)
                current += 1
                if current % 50 == 0:
                    LOGGER.info(u'Archived %s/%s duplicate articles so far.',
                                current, counts['duplicates'])

    if counts['orphaned']:
        current = 0
        LOGGER.info(u'Archiving of %s orphaned article(s) started.',
                    counts['orphaned'])

        with benchmark('Archiving of %s orphaned article(s)'
                       % counts['orphaned']):
            for article in orphaned:
                archive_article_one_internal(article, counts)
                current += 1
                if current % 50 == 0:
                    LOGGER.info(u'Archived %s/%s orphaned articles so far.',
                                current, counts['duplicates'])

    if counts['duplicates'] or counts['orphaned']:
        synchronize_statsd_articles_gauges(full=True)

        LOGGER.info('%s already archived and %s bad articles were found '
                    u'during the operation.', counts['archived_dupes'],
                    counts['bad_articles'])

    else:
        LOGGER.info(u'No article to archive.')


@task(queue='clean')
def archive_documents(limit=None, force=False):
    """ Archive all kind of documents that need archiving. """

    if config.DOCUMENTS_ARCHIVING_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'Document archiving disabled in configuration.')
        return

    # Be sure two archiving operations don't overlap, this is a very costly
    # operation for the database, and it can make the system very slugish.
    # The whole operation can be very long, we lock for a long time.
    my_lock = RedisExpiringLock('archive_documents', expire_time=3600 * 24)

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'archive_documents() force unlock/re-acquire, '
                           u'be careful with that.')

        else:
            LOGGER.warning(u'archive_documents() is already locked, aborting.')
            return

    # these are tasks, but we run them sequentially in this global archive job
    # to avoid hammering the production database with multiple archive jobs.
    archive_articles(limit=limit)

    my_lock.release()
