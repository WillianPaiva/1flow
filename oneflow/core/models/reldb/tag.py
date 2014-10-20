# -*- coding: utf-8 -*-
"""
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

from statsd import statsd

# from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from mptt.models import MPTTModel, TreeForeignKey

from oneflow.base.utils import register_task_method

from language import Language

LOGGER = logging.getLogger(__name__)


__all__ = ['SimpleTag', ]


class SimpleTag(MPTTModel):

    """ A simple tag model, with language and tag hierarchy if needed. """

    name     = models.CharField(verbose_name=_(u'name'), max_length=128)
    slug     = models.CharField(verbose_name=_(u'slug'),
                                max_length=128, null=True)
    language = models.ForeignKey(Language, null=True)

    parent   = TreeForeignKey('self', null=True, blank=True,
                              related_name='children')

    origin_type = models.ForeignKey(ContentType)
    origin_id = models.PositiveIntegerField()
    origin = generic.GenericForeignKey('origin_type', 'origin_id')

    duplicate_of = models.ForeignKey(
        'self', verbose_name=_(u'Duplicate of'),
        help_text=_(u'Put a "master" tag here to help avoiding too much '
                    u'different tags (eg. singular and plurals) '
                    u'with the same meaning and loss of information.'))

    class Meta:
        app_label = 'core'
        unique_together = ('name', 'language', )
        verbose_name = _(u'Tag')
        verbose_name_plural = _(u'Tags')

    class MPTTMeta:
        order_insertion_by = ['name']

    # See the `WordRelation` class before working on this.
    #
    # antonyms = ListField(ReferenceField('self'), verbose_name=_(u'Antonyms'),
    #                      help_text=_(u'Define an antonym tag to '
    #                      u'help search connectable but.'))

    def __unicode__(self):
        """ Unicode, pep257. """

        return _(u'{0} {1}⚐ (#{2})').format(self.name, self.language, self.id)

    def replace_duplicate_everywhere(self, duplicate_id, *args, **kwargs):
        """ When a Tag is marked as duplicate of another.

        Do the necessary dirty work of replacing it everywhere it's
        needed to keep the database clean, in order to eventually delete
        the duplicate one day.

        .. note:: for tags, deleting duplicates is not an option and is
            even a feature, to allow keeping things unified between users
            (eg. use the same tags in search engine…).
        """

        duplicate = self.__class__.objects.get(id=duplicate_id)

        # This method is defined in nonrel.article to avoid an import loop.
        self.replace_duplicate_in_articles(duplicate, *args, **kwargs)
        #
        # TODO: do the same for feeds, reads (, subscriptions?) …
        #
        pass

    @classmethod
    def get_tags_set(cls, tags_names, origin=None):
        """ Given a list of strings, return a set of tags. """

        tags = set()

        for tag_name in tags_names:
            tag_name = tag_name.lower()

            tag, created = cls.objects.get_or_create(name=tag_name)

            if created and origin:
                tag.origin = origin
                tag.save()

            tags.add(tag.duplicate_of or tag)

        return tags

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            self.slug = slugify(self.name)
            self.save()

            statsd.gauge('tags.counts.total', 1, delta=True)


# ———————————————————————————————————————————————————————————— Methods as tasks


register_task_method(SimpleTag,
                     SimpleTag.post_create_task,
                     globals(), u'high')
register_task_method(SimpleTag,
                     SimpleTag.replace_duplicate_everywhere,
                     globals(), u'low')


# ————————————————————————————————————————————————————————————————————— Signals


def simpletag_post_save(instance, **kwargs):

    if kwargs.get('created', False):
        # HEADS UP: this task is declared by
        # the register_task_method call below.
        simpletag_post_create_task.delay(instance.id)  # NOQA


post_save.connect(simpletag_post_save, sender=SimpleTag)
