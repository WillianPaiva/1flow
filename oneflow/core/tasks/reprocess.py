# -*- coding: utf-8 -*-
u"""
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

from celery import task

# from django.utils.translation import ugettext_lazy as _

from ..models.reldb import (
    Article,
    article_post_create_task,
)

from oneflow.base.utils import RedisExpiringLock
from oneflow.base.utils.dateutils import naturaldelta, benchmark

LOGGER = logging.getLogger(__name__)


@task(name='oneflow.core.tasks.reprocess_failed_articles', queue='check')
def reprocess_failed_articles(failed=None, expiry=None,
                              limit=None, force=False):
    u""" Reprocess articles that failed absolutization.

    In case there was a temporary error, this could lead to more good articles.
    """

    if config.ARTICLE_REPROCESSING_DISABLED:
        # Do not raise any .retry(), this is a scheduled task.
        LOGGER.warning(u'Articles reprocess disabled in configuration.')
        return

    if failed is None:
        failed = Article.objects.url_error().created_previous_hour()
        expiry = 3500

    my_lock = RedisExpiringLock(
        'reprocess_failed_articles_' + str(expiry),
        expire_time=expiry
    )

    if not my_lock.acquire():
        if force:
            my_lock.release()
            my_lock.acquire()
            LOGGER.warning(u'Forcing failed articles reprocessing…')

        else:
            # Avoid running this task over and over again in the queue
            # if the previous instance did not yet terminate. Happens
            # when scheduled task runs too quickly.
            LOGGER.warning(u'reprocess_failed_articles() is already locked, '
                           u'aborting.')
            return

    failed_count = failed.count()

    with benchmark((u'Reprocess_failed_articles(expiry=%s): %s '
                   u'post_create() tasks chains relaunched.')
                   % (naturaldelta(expiry), failed_count)):

        try:
            for article in failed:
                article.url_error = None
                article.save()

                article_post_create_task.apply(args=(article.id, ),
                                               kwargs={'apply_now': True})

        finally:
            # HEADS UP: in case the system is overloaded, we intentionaly
            #           don't release the lock to avoid over-re-launched
            #           global tasks to flood the queue with useless
            #           double-triple-Nble individual tasks.
            #
            # my_lock.release()
            pass


@task(name='oneflow.core.tasks.reprocess_failed_articles_pass2',
      queue='check')
def reprocess_failed_articles_pass2(limit=None, force=False):
    """ Run reprocess_failed_articles() on articles from yesterday. """

    failed = Article.objects.url_error().created_previous_day()
    expiry = 3600 * 23

    reprocess_failed_articles(failed=failed, expiry=expiry,
                              limit=limit, force=force)


@task(name='oneflow.core.tasks.reprocess_failed_articles_pass3',
      queue='check')
def reprocess_failed_articles_pass3(limit=None, force=False):
    """ Run reprocess_failed_articles() on articles from last week. """

    failed = Article.objects.url_error().created_previous_week()
    expiry = 3600 * 24 * 6

    reprocess_failed_articles(failed=failed, expiry=expiry,
                              limit=limit, force=force)
