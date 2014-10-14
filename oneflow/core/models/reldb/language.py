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

from django.db import models
from django.utils.translation import ugettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey

LOGGER = logging.getLogger(__name__)


__all__ = ['Language', ]


class Language(MPTTModel):

    """ Language model, with hierarchy for grouping. """

    name    = models.CharField(verbose_name=_(u'name'), max_length=128)
    dj_code = models.CharField(verbose_name=_(u'Django code'),
                               max_length=16, unique=True)
    parent  = TreeForeignKey('self', null=True, blank=True,
                             related_name='children')

    duplicate_of = models.ForeignKey(
        'self', verbose_name=_(u'Duplicate of'))

    class Meta:
        app_label = 'core'
        verbose_name = _(u'models.language.verbose_name')
        verbose_name_plural = _(u'models.language.verbose_name_plural')

    class MPTTMeta:
        order_insertion_by = ['name']

    def __unicode__(self):
        """ Unicode, pep257. """

        return _(u'{0}⚐ (#{1})').format(self.name, self.id)
