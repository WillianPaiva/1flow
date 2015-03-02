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


__all__ = [
    'Language',
    'AbstractMultipleLanguagesModel',
    'AbstractLanguageAwareModel',
]


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

    # https://docs.djangoproject.com/en/dev/topics/i18n/
    dj_code = models.CharField(verbose_name=_(u'Language code'),
                               max_length=16, unique=True,
                               help_text=_(u'This is the IETF code.'))

    iso639_1 = models.CharField(
        verbose_name=_(u'ISO-639-1 code'),
        max_length=16, null=True, blank=True,
        help_text=_(u'This is a 2-letters code. Some languages do not '
                    u'have any. But all have an ISO-639-2 or -3 one. '
                    u'Sometimes it is the same as the IETF (Django) one.'))

    iso639_2 = models.CharField(
        verbose_name=_(u'ISO-639-2 code'),
        max_length=16, null=True, blank=True)

    iso639_3 = models.CharField(
        verbose_name=_(u'ISO-639-3 code'),
        max_length=16, null=True, blank=True)

    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')

    # ————————————————————————————————————————————————————————— Python / Django

    def __unicode__(self):
        """ Unicode, pep257. """

        iso_code = self.iso639_1 or self.iso639_2 or self.iso639_3

        return _(u'{0} (ID: {1}) {2}{3}').format(
            self.name, self.id, self.dj_code,
            u', {0}'.format(iso_code) if iso_code else u' (no ISO code)')

    # ——————————————————————————————————————————————————————————— Class methods

    @classmethod
    def get_by_code(cls, code):
        """ Return the language associated with code (insensitive).

        This will create the language if needed. If the language is not
        lowercase, this will also trigger a register_duplicate() process
        and return the lowercase language instead.
        """

        try:
            language = cls.objects.get(dj_code=code)

        except cls.DoesNotExist:
            language = cls(name=code.title(), dj_code=code)
            language.save()

        if language.duplicate_of_id is not None:
            return language.duplicate_of

        if code != code.lower():
            # We just found a duplicate !
            lower_language = cls.get_by_code(code.lower())
            lower_language.register_duplicate(language)
            return lower_language

        return language

    def replace_duplicate(self, duplicate, *args, **kwargs):
        """ Replace a duplicate language by another. """

        all_went_ok = True

        if not self.abstract_replace_duplicate(
            duplicate=duplicate,
            abstract_model=AbstractMultipleLanguagesModel,
            field_name='languages',
            many_to_many=True
        ):
            all_went_ok = False

        if not self.abstract_replace_duplicate(
            duplicate=duplicate,
            abstract_model=AbstractLanguageAwareModel,
            field_name='language',
            many_to_many=False
        ):
            all_went_ok = False

        return all_went_ok


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
