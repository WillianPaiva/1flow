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

import six
import logging

# from statsd import statsd
# from constance import config
from transmeta import TransMeta
# from json_field import JSONField
# from collections import OrderedDict
# from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save  # , post_save, pre_delete
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

try:
    # Django 1.7
    from django.apps import apps
    get_model = apps.get_model

except:
    # Older Django
    from django.db.models.loading import get_model

from mptt.models import MPTTModelBase, MPTTModel, TreeForeignKey
from sparks.django.models.mixins import DiffMixin

# from oneflow.base.utils.http import split_url

from ..common import DjangoUser as User  # ORIGINS,

LOGGER = logging.getLogger(__name__)


__all__ = [
    'ProcessorCategory',
]


# ————————————————————————————————————————————————————————————— Class & related

class ProcessorCategoryMeta(MPTTModelBase, TransMeta):

    """ This one follows the BaseFeedMeta idea. """

    pass


class ProcessorCategory(six.with_metaclass(ProcessorCategoryMeta,
                        MPTTModel, DiffMixin)):

    """ A simple multilingual category system for processors. """

    class Meta:
        app_label = 'core'
        verbose_name = _(u'Processor category')
        verbose_name_plural = _(u'Processor categories')
        translate = ('name', 'short_description', 'description', )

    name = models.CharField(
        max_length=128,
        verbose_name=_(u'Name'),
    )

    slug = models.CharField(
        max_length=128,
        verbose_name=_(u'slug'),
        null=True, blank=True
    )

    user = models.ForeignKey(User,
                             null=True, blank=True,
                             verbose_name=_(u'Creator'),
                             related_name='processor_categories')

    maintainer = models.ForeignKey(
        User,
        null=True, blank=True,
        verbose_name=_(u'Maintainer'),
        related_name='maintained_categories'
    )

    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')

    is_active = models.BooleanField(default=True)

    source_address = models.CharField(
        null=True, blank=True,
        max_length=384, verbose_name=_(u'Source address'),
        help_text=_(u'The category home on the web, if any. A web URL, '
                    u'or a github short address.'))

    short_description = models.CharField(
        null=True, blank=True,
        max_length=256, verbose_name=_(u'Short description'))

    description = models.TextField(
        null=True, blank=True,
        verbose_name=_(u'Description'))

    def __unicode__(self):
        """ Hello pep257. I love you. """

        return self.slug


def processorcategory_pre_save(instance, **kwargs):
    """ Do pre_save work. """

    if instance.slug is None or instance.slug.strip() == u'':
        instance.slug = slugify(instance.name)

    # The following part must always come last, to
    # also detect automatic changes to the slug.

    diff = instance.diff

    if 'slug' in diff:

        LOGGER.info(u'%s: slug changed, updating processors…', instance)

        old_slug = diff['slug'][0]
        new_slug = diff['slug'][1]

        for processor in get_model('core', 'Processor').objects.all():
            processor.update_changed_slug(old_slug, new_slug)


# def processor_post_save(instance, **kwargs):
#   """ Do post_save work. """
#
#     if kwargs.get('created', False):
#         return


pre_save.connect(processorcategory_pre_save, sender=ProcessorCategory)
# post_save.connect(processor_post_save, sender=Processor)
