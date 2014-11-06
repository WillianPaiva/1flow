# -*- coding: utf-8 -*-
"""
Repair missing BaseItem from the migration.

I didn't find why they are missing, but this produces strange errors, where
Article objects are present and throw integrity errors while not beiing able
to get() the articles back in the app.

"""

import logging


from django.db import connection

from oneflow.core.models import BaseItem, Article
from oneflow.core.models.nonrel import Article as MongoArticle


LOGGER = logging.getLogger(__name__)


def repair_missing_baseitems(fix_title=True, number=None):
    """ FIX the missing base items. """

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT baseitem_ptr_id
        FROM core_article
        WHERE core_article.baseitem_ptr_id NOT IN (
            SELECT id
            FROM core_baseitem
        ) LIMIT %s;
        """,
        [number or 100000]
    )

    done = 0
    value = cursor.fetchone()

    while value:
        bid = value[0]

        try:
            b = BaseItem(
                id=bid,

                # Set a name we can query back without
                # messing more if anything goes wrong.
                name=u"@]-[@REPAIR@]-[@",

                # Manually set the type to Article.
                polymorphic_ctype_id=57
            )
            b.save()

        except:
            LOGGER.exception(u'Could not create BaseItem with ID %s', bid)
            break

        if fix_title:
            try:
                article = Article.objects.get(baseitem_ptr_id=bid)
                article.name = MongoArticle.objects.get(
                    url=article.url).title
                article.save()

            except:
                LOGGER.exception(u'Could not set title of %s', bid)

        if done % 100 == 0:
            LOGGER.info(u'Repaired (at %s) >>> %s', done, article)

        done += 1
        value = cursor.fetchone()

    # for article in Article.objects.filter(name__startswith='@]-[@REPAIR@]-[@'):  # NOQA
    #     article.name = MongoArticle.objects.get(url=article.url)
    #     article.save()
