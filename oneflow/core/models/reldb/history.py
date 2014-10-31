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

from polymorphic import PolymorphicModel

# from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

# from oneflow.base.utils import register_task_method
from oneflow.base.utils.dateutils import now

from common import DjangoUser  # , REDIS

LOGGER = logging.getLogger(__name__)


__all__ = ['HistoryEntry', ]


class HistoryEntry(PolymorphicModel):

    """ A simple history system to keep track of what happened. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'history line')
        verbose_name_plural = _(u'History lines')

    user = models.ForeignKey(DjangoUser, verbose_name=_(u'Owner'))
    date_created = models.DateTimeField(auto_now_add=True, default=now,
                                        verbose_name=_(u'date created'))

    @property
    def get_class_name(self):
        """ Get the __name__ for the templating engine. """

        try:
            return self.__name__

        except AttributeError:
            return self.__class__.__name__
