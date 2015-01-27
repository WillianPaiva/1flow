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

from positions import PositionField

# from statsd import statsd
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

from chain import ProcessingChain
# from processor import Processor

LOGGER = logging.getLogger(__name__)


__all__ = [
    'ChainedItem',
    'ChainedItemManager',
]


# ————————————————————————————————————————————————————————————— Class & related


class ChainedItemManager(models.Manager):

    """ Simple manager with natural keys support. """

    def get_by_natural_key(self, chain, position):
        """ Get by chain & position. """

        return self.get(chain=chain, position=position)


class ChainedItem(models.Model):

    """ parameters of a given item in a given chain.

    Processors and other chains can appear in any chain at any position.
    This depends on the complexity of the parent chain. The current model
    holds the position and the optional arguments of all chained items.

    """

    __metaclass__ = TransMeta

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Chained item')
        verbose_name_plural = _(u'Chained items')
        translate = ('notes', )

    objects = ChainedItemManager()

    chain = models.ForeignKey(ProcessingChain, related_name='chained_items')

    item_type = models.ForeignKey(
        ContentType, null=True, blank=True,
        limit_choices_to=(
            models.Q(app_label='core')
            & (
                # HEADS UP: “Processor” (title case, model name) does
                # not find anything. “processor” (lowercase) works. See:
                #
                # ContentType.objects.filter(
                #   app_label='core').values_list(
                #       'model', flat=True)
                #
                # For a complete list of valid values.
                models.Q(model='processor')
                | models.Q(model='processingchain')
            )
        )
    )
    item_id = models.PositiveIntegerField(null=True, blank=True)
    item = generic.GenericForeignKey('item_type', 'item_id')

    position = PositionField(collection=('chain', ), default=0, blank=True)

    is_active = models.BooleanField(default=True)

    # NOT READY. SHould probably be implemented by a real workflow engine.
    # condition =

    # This should probably be a JSON field…
    parameters = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Chain parameters'),
        help_text=_(u'Global parameters for this processor, '
                    u'in this chain, at this position. Can be '
                    u'none if the processor accepts only site-specific '
                    u'parameters. Can be overridden by the site-specific '
                    u'parameters, at the web site configuration level.'))

    is_valid = models.BooleanField(verbose_name=_(u'Checked and valid'),
                                   default=True, blank=True)

    check_error = models.CharField(max_length=255, null=True, blank=True)

    notes = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Notes'),
        help_text=_(u'Things to know about this processor, '
                    u'in this chain, at this position.'))

    # ————————————————————————————————————————————————————————— Python & Django

    def __unicode__(self):
        """ I'm __unicode__, pep257. """

        return (
            u'Chain {0} pos. {1}: {2} {3} (#{4})'.format(
                self.chain.slug,
                self.position,
                self.item._meta.verbose_name,
                self.item.slug,
                self.id)
        )

    def natural_key(self):
        """ This is needed for serialization. """

        return (self.chain, self.position)

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
