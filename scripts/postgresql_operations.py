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

import logging

# from constance import config

# from celery import task

from django.db import connection
from oneflow.base.utils.dateutils import benchmark, now
from oneflow.core.tasks.migration import vacuum_analyze


LOGGER = logging.getLogger(__name__)


def do_whatever_SQL(query, qargs, pretty_name):
    """ Go ahead, man. """

    with benchmark(pretty_name):
        cursor = connection.cursor()
        cursor.execute(query, qargs)
        try:
            return cursor.fetchone()[0]

        except:
            return None


def go(limit=None, all_hint=None):
    """ Do the dirty things, fast. """

    TO_CLEAN = ('url', 'content', )

    URL_CLEANING_QUERY = """
UPDATE core_article SET {0}_error = NULL
WHERE core_article.baseitem_ptr_id IN (
    SELECT baseitem_ptr_id
    FROM core_article
    WHERE {0}_error = ''
    LIMIT {1}
);
"""

    COUNT_QUERY = """
SELECT COUNT(*)
FROM core_article
WHERE {0}_error = '';
"""

    if limit is None:
        limit = 50000

    if all_hint is None:
        all_hint = 7000000

    LOGGER.info(u'Starting to fix the world @ %s', now())

    with benchmark(u'Fix everything'):

        for to_clean in TO_CLEAN:

            done = 0

            with benchmark(u'Fixing %s' % to_clean):
                while True:
                    do_whatever_SQL(
                        URL_CLEANING_QUERY.format(
                            to_clean, limit
                        ),
                        [],
                        u'Fixing %s, round %s' % (to_clean, done)
                    )

                    done += 1

                    if done % 5 == 0:
                        vacuum_analyze()

                    if done > (all_hint / limit):
                        count = do_whatever_SQL(
                            COUNT_QUERY.format(to_clean),
                            [],
                            u'Counting things'
                        )
                        if count == 0:
                            break
