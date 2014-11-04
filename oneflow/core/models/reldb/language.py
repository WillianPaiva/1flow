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

from django.db import models
from django.utils.translation import ugettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey

from duplicate import AbstractDuplicateAwareModel

LOGGER = logging.getLogger(__name__)


__all__ = ['Language', ]


class Language(MPTTModel, AbstractDuplicateAwareModel):

    """ Language model, with hierarchy for grouping. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Language')
        verbose_name_plural = _(u'Languages')

    class MPTTMeta:
        order_insertion_by = ['name']

    name = models.CharField(verbose_name=_(u'name'),
                            max_length=128, blank=True)

    dj_code = models.CharField(verbose_name=_(u'Django code'),
                               max_length=16, unique=True)

    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')

    # ————————————————————————————————————————————————————————— Python / Django

    def __unicode__(self):
        """ Unicode, pep257. """

        return _(u'{0}⚐ (#{1})').format(self.name, self.id)

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def get_by_code(cls, code):
        """ Return the language associated with code, creating it if needed. """
        try:
            language = cls.objects.get(dj_code=code)

        except cls.DoesNotExist:
            language = cls(name=code.title(), dj_code=code)
            language.save()

        if language.duplicate_of:
            return language.duplicate_of

        return language

    def replace_duplicate(self, duplicate, *args, **kwargs):
        u""" When a Tag is marked as duplicate of another.

        Do the necessary dirty work of replacing it everywhere. It's
        needed to keep the database clean, in order to eventually do
        something with the duplicate one day.

        .. note:: for tags, deleting duplicates is not an option and it's
            even a feature: this allows keeping things unified between
            users (eg. use the same tags in search engine…).
        """

        # Get all concrete classes that inherit from AbstractMultipleLanguagesModel  # NOQA
        for model in AbstractMultipleLanguagesModel.__subclasses__():

            # For each concrete class, get each instance
            for instance in model.objects.all():

                try:
                    # Replace the duplicate tag by the master.
                    instance.languages.remove(duplicate)
                    instance.languages.add(self)

                except:
                    LOGGER.exception(u'Replacing language duplicate %s by %s '
                                     u'failed in %s %s', duplicate, self,
                                     model.__name__, instance)

        # Get all concrete classes that inherit from AbstractLanguageAwareModel
        for model in AbstractLanguageAwareModel.__subclasses__():

            # For each concrete class, get each instance
            for instance in model.objects.all():

                try:
                    # Replace the duplicate tag by the master.
                    instance.language = self

                except:
                    LOGGER.exception(u'Replacing language duplicate %s by %s '
                                     u'failed in %s %s', duplicate, self,
                                     model.__name__, instance)

                else:
                    instance.save()


class AbstractMultipleLanguagesModel(models.Model):

    class Meta:
        abstract = True
        app_label = 'core'

    languages = models.ManyToManyField(
        Language, verbose_name=_(u'Languages'),
        blank=True, null=True)


class AbstractLanguageAwareModel(models.Model):

    class Meta:
        abstract = True
        app_label = 'core'

    language = models.ForeignKey(
        Language, verbose_name=_(u'Language'),
        blank=True, null=True, db_index=True)
