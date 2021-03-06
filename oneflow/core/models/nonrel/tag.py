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

from statsd import statsd

from pymongo.errors import DuplicateKeyError

from mongoengine import Document, NULLIFY, PULL
from mongoengine.fields import (StringField, ReferenceField, ListField,
                                GenericReferenceField, BooleanField)
from mongoengine.errors import NotUniqueError

from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from ....base.utils import register_task_method

from .common import DocumentHelperMixin


LOGGER = logging.getLogger(__name__)


__all__ = ['Tag', ]


class Tag(Document, DocumentHelperMixin):

    # BIG DB migration 20141028
    bigmig_migrated = BooleanField(default=False)
    # END BIG DB migration

    name     = StringField(verbose_name=_(u'name'), unique=True)
    slug     = StringField(verbose_name=_(u'slug'))
    language = StringField(verbose_name=_(u'language'), default='')
    parents  = ListField(ReferenceField('self',
                         reverse_delete_rule=PULL), default=list)
    children = ListField(ReferenceField('self',
                         reverse_delete_rule=PULL), default=list)
    # reverse_delete_rule=NULLIFY,
    origin   = GenericReferenceField(verbose_name=_(u'Origin'),
                                     help_text=_(u'Initial origin from where '
                                                 u'the tag was created from, '
                                                 u'to eventually help '
                                                 u'defining other attributes.'))
    duplicate_of = ReferenceField('Tag', reverse_delete_rule=NULLIFY,
                                  verbose_name=_(u'Duplicate of'),
                                  help_text=_(u'Put a "master" tag here to '
                                              u'help avoiding too much '
                                              u'different tags (eg. singular '
                                              u'and plurals) with the same '
                                              u'meaning and loss of '
                                              u'information.'))

    meta = {
        'indexes': ['name', ]
    }

    # See the `WordRelation` class before working on this.
    #
    # antonyms = ListField(ReferenceField('self'), verbose_name=_(u'Antonyms'),
    #                      help_text=_(u'Define an antonym tag to '
    #                      u'help search connectable but.'))

    def __unicode__(self):
        return _(u'{0} {1}⚐ (#{2})').format(self.name, self.language, self.id)

    def replace_duplicate_everywhere(self, duplicate_id, *args, **kwargs):

        duplicate = self.__class__.objects.get(id=duplicate_id)

        # This method is defined in nonrel.article to avoid an import loop.
        self.replace_duplicate_in_articles(duplicate, *args, **kwargs)
        #
        # TODO: do the same for feeds, reads (, subscriptions?) …
        #
        pass

    @classmethod
    def signal_post_save_handler(cls, sender, document,
                                 created=False, **kwargs):

        tag = document

        if created:
            if tag._db_name != settings.MONGODB_NAME_ARCHIVE:

                # HEADS UP: this task is declared by
                # the register_task_method call below.
                tag_post_create_task.delay(tag.id)  # NOQA

    def post_create_task(self):
        """ Method meant to be run from a celery task. """

        if not self.slug:
            self.slug = slugify(self.name)
            self.save()

            statsd.gauge('mongo.tags.counts.total', 1, delta=True)

    @classmethod
    def get_tags_set(cls, tags_names, origin=None):

        tags = set()

        for tag_name in tags_names:
            tag_name = tag_name.lower()

            try:
                tag = cls.objects.get(name=tag_name)

            except cls.DoesNotExist:
                try:
                    tag = cls(name=tag_name, origin=origin).save()

                except (NotUniqueError, DuplicateKeyError):
                    tag = cls.objects.get(name=tag_name)

            tags.add(tag.duplicate_of or tag)

        return tags

    def save(self, *args, **kwargs):
        """ This method will simply add the missing children/parents reverse
            links of the current Tag. This is needed when modifying tags from
            the Django admin, which doesn't know about the reverse-link
            existence.

            .. note:: sadly, we have no fast way to do the same for links
                removal.
        """

        super(Tag, self).save(*args, **kwargs)

        for parent in self.parents:
            if self in parent.children:
                continue

            try:
                parent.add_child(self, update_reverse_link=False,
                                 full_reload=False)
            except:
                LOGGER.exception(u'Exception while reverse-adding '
                                 u'child %s to parent %s', self, parent)

        for child in self.children:
            if self in child.parents:
                continue

            try:
                child.add_parent(self, update_reverse_link=False,
                                 full_reload=False)
            except:
                LOGGER.exception(u'Exception while reverse-adding '
                                 u'parent %s to child %s', self, child)

        return self

    def add_parent(self, parent, update_reverse_link=True, full_reload=True):

        self.update(add_to_set__parents=parent)

        if full_reload:
            self.safe_reload()

        if update_reverse_link:
            parent.add_child(self, update_reverse_link=False)

    def remove_parent(self, parent, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            parent.remove_child(self, update_reverse_link=False)

        self.update(pull__parents=parent)

        if full_reload:
            self.safe_reload()

    def add_child(self, child, update_reverse_link=True, full_reload=True):
        self.update(add_to_set__children=child)

        if full_reload:
            self.safe_reload()

        if update_reverse_link:
            child.add_parent(self, update_reverse_link=False)

    def remove_child(self, child, update_reverse_link=True, full_reload=True):

        if update_reverse_link:
            child.remove_parent(self, update_reverse_link=False)

        self.update(pull__children=child)

        if full_reload:
            self.safe_reload()


register_task_method(Tag, Tag.post_create_task, globals(), queue=u'high')
register_task_method(Tag, Tag.replace_duplicate_everywhere, globals(), queue=u'low')
