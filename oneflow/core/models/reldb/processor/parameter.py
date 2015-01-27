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
# import uuid
import logging

# from constance import config
from transmeta import TransMeta
# from json_field import JSONField

from django.db import models
# from django.db.models.signals import post_save, pre_save  # , pre_delete
from django.utils.translation import ugettext_lazy as _
# from django.utils.text import slugify

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

# from ..common import DjangoUser as User  # ORIGINS,

from chaineditem import ChainedItem

LOGGER = logging.getLogger(__name__)


__all__ = [
    'ChainedItemParameter',
]


# ————————————————————————————————————————————————————————————— Class & related


class ChainedItemParameter(models.Model):

    """ parameters of a chained item for a given 1flow instance.

    We talk here about the parameters for {website,article,…} X processed
    by chained item Y of Chain Z.

    Item Y already has default (global, non-instance dependant) parameters
    stored inside itself. The current model stores parameters for any other
    1flow instance, if necessary.
    """

    __metaclass__ = TransMeta

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Chained item parameter')
        verbose_name_plural = _(u'Chained item parameters')
        translate = ('notes', )

    item = models.ForeignKey(ChainedItem)

    instance_type = models.ForeignKey(ContentType, null=True, blank=True)
    instance_id = models.PositiveIntegerField(null=True, blank=True)
    instance = generic.GenericForeignKey('instance_type', 'instance_id')

    # This should probably be a JSON field…
    parameters = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Chained item parameters'),
        help_text=_(u'Specific parameters for this chained '
                    u'item AND this instance. Can be none.'))

    is_valid = models.BooleanField(verbose_name=_(u'Checked and valid'),
                                   default=True, blank=True)

    check_error = models.CharField(max_length=255, null=True, blank=True)

    notes = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Notes')
    )

    # ————————————————————————————————————————————————————————— Python & Django

    def __unicode__(self):
        """ I'm __unicode__, pep257. """

        return (
            u'Chain {0} position #{1}: {2} (#{3})'.format(
                self.chain.name,
                self.position,
                self.processor.name,
                self.id)
        )

    # ——————————————————————————————————————————————————————————— Class methods


# ————————————————————————————————————————————————————————————————————— Signals


# def chained_processor_pre_save(instance, **kwargs):
#     """ Method meant to be run from a celery task. """

#     return


# def chained_processor_post_save(instance, **kwargs):

#     if kwargs.get('created', False):
#         return


# pre_save.connect(chained_processor_pre_save, sender=ChainedItem)
# post_save.connect(chained_processor_post_save, sender=ChainedItem)
