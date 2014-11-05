# -*- coding: utf-8 -*-
u"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

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

from django.contrib import admin
# from django.utils.translation import ugettext_lazy as _

# from django_object_actions import DjangoObjectActions

# from ..models.common import DUPLICATE_STATUS
from ..models.reldb import (  # NOQA
    Language,
    abstract_replace_duplicate_task
)

LOGGER = logging.getLogger(__name__)


class LanguageAdmin(admin.ModelAdmin):

    """ Language admin class. """

    list_display = (
        'id', 'name', 'dj_code',
        'iso639_1', 'iso639_2', 'iso639_3',
        'parent',
        'duplicate_of',
        'duplicate_status',
    )
    list_display_links = ('id', 'name', )
    list_filter = ('parent', 'duplicate_status', )
    ordering = ('dj_code', )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    search_fields = ('name', 'dj_code', 'iso639_1', 'iso639_2', 'iso639_3', )

    # def get_object_actions(self, request, context, **kwargs):
    #     """ Get object actions. """

    #     objectactions = []

    #     # Actions cannot be applied to new objects (i.e. Using "add" new obj)
    #     if 'original' in context:
    #         # The obj to perform checks against to determine
    #         # object actions you want to support.
    #         obj = context['original']

    #     LOGGER.warning('YALLAAA')

    #     if obj.duplicate_of:
    #         if obj.duplicate_status in (DUPLICATE_STATUS.NOT_REPLACED,
    #                                     DUPLICATE_STATUS.FAILED, ):
    #             objectactions.append('replace_duplicate_again')

    #     return objectactions

    # def replace_duplicate_again(self, request, obj):
    #     """ Re-run the replace_duplicate() task. """

    #     abstract_replace_duplicate_task.delay(obj._meta.app_label,
    #                                           obj._meta.object_name,
    #                                           obj.id,
    #                                           obj.duplicate_of.id)

    # replace_duplicate_again.label = _(u'Replace again')
    # replace_duplicate_again.short_description = \
    #     _(u'Re-run the replace_duplicate() task.')
