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

from statsd import statsd

# from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from mptt.models import MPTTModel, TreeForeignKey

from duplicate import AbstractDuplicateAwareModel
from language import Language

LOGGER = logging.getLogger(__name__)


__all__ = ['SimpleTag', ]


class SimpleTag(MPTTModel, AbstractDuplicateAwareModel):

    """ A simple tag model, with language and tag hierarchy if needed. """

    name     = models.CharField(verbose_name=_(u'name'), max_length=128)
    slug     = models.CharField(verbose_name=_(u'slug'),
    language = models.ForeignKey(Language, null=True)

    parent   = TreeForeignKey('self', null=True, blank=True,
                              related_name='children')

    origin_type = models.ForeignKey(ContentType, null=True, blank=True)
    origin_id = models.PositiveIntegerField(null=True, blank=True)
    origin = generic.GenericForeignKey('origin_type', 'origin_id')

    class Meta:
        app_label = 'core'
        unique_together = ('name', 'language', )
        verbose_name = _(u'Tag')
        verbose_name_plural = _(u'Tags')

    # class MPTTMeta:
    #     order_insertion_by = ['name']

    # See the `WordRelation` class before working on this.
    #
    # antonyms = ListField(ReferenceField('self'), verbose_name=_(u'Antonyms'),
    #                      help_text=_(u'Define an antonym tag to '
    #                      u'help search connectable but.'))

    def __unicode__(self):
        """ Unicode, pep257. """

        return _(u'{0} {1}⚐ (#{2})').format(self.name, self.language, self.id)

    def replace_duplicate(self, duplicate, *args, **kwargs):
        u""" When a Tag is marked as duplicate of another.

        Do the necessary dirty work of replacing it everywhere. It's
        needed to keep the database clean, in order to eventually do
        something with the duplicate one day.

        .. note:: for tags, deleting duplicates is not an option and it's
            even a feature: this allows keeping things unified between
            users (eg. use the same tags in search engine…).
        """

        sub_classes = AbstractTaggedModel.__subclasses__()
        sub_classes_count = len(sub_classes)

        LOGGER.info(u'Replacing tag duplicate %s by master %s '
                    u'in %s models (%s)…', duplicate, self,
                    sub_classes_count,
                    u', '.join(m.__name__ for m in sub_classes))

        all_models_all_instances_count = 0
        all_models_all_failed_count = 0

        # Get all concrete classes that inherit from AbstractTaggedModel
        for model in sub_classes:

            verbose_name = model._meta.verbose_name
            verbose_name_plural = model._meta.verbose_name_plural

            all_instances = model.objects.all()
            all_instances_count = all_instances.count()
            failed_instances_count = 0

            LOGGER.info(u'Replacing tag duplicate %s by master %s '
                        u'in %s %s instances…', duplicate, self,
                        all_instances_count, verbose_name)

            # For each concrete class, get each instance
            for instance in all_instances:

                try:
                    # Replace the duplicate tag by the master.
                    instance.tags.remove(duplicate)
                    instance.tags.add(self)

                except:
                    failed_instances_count += 1
                    LOGGER.exception(u'Replacing tag duplicate %s by %s '
                                     u'failed in %s %s', duplicate, self,
                                     verbose_name, instance)

            all_models_all_instances_count += all_instances_count
            all_models_all_failed_count += failed_instances_count

            LOGGER.info(u'Replaced tag duplicate %s by %s in %s %s '
                        u'(%s failed).', duplicate, self,
                        all_instances_count - failed_instances_count,
                        verbose_name_plural,
                        failed_instances_count)

        LOGGER.info(u'Done replacing tag duplicate %s by %s in %s models: '
                    u'%s instances processed, %s failed.', duplicate, self,
                    sub_classes_count,
                    all_models_all_instances_count,
                    all_models_all_failed_count)

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


class AbstractTaggedModel(models.Model):

    class Meta:
        abstract = True
        app_label = 'core'

    tags = models.ManyToManyField(
        SimpleTag, verbose_name=_(u'Tags'),
        blank=True, null=True)


# ————————————————————————————————————————————————————————————————————— Signals


def simpletag_pre_save(instance, **kwargs):

    LOGGER.info(u'--%s--', instance.slug)

    if not instance.slug:
        instance.slug = slugify(instance.name)


def simpletag_post_save(instance, **kwargs):

    if kwargs.get('created', False):
        statsd.gauge('tags.counts.total', 1, delta=True)


pre_save.connect(simpletag_pre_save, sender=SimpleTag)
post_save.connect(simpletag_post_save, sender=SimpleTag)
