# -*- coding: utf-8 -*-
u"""
Copyright 2015 Olivier Cortès <oc@1flow.io>.

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

from django.conf import settings
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _  # , pgettext_lazy

from ..models.reldb import (  # NOQA
    Processor,
    ProcessingChain,
    ChainedItem,
    ChainedItemParameter,
    ProcessingError,
    ProcessorCategory,
)
from django import forms
from codemirror import CodeMirrorTextarea


class ProcessorAdminForm(forms.ModelForm):

    """ Use CodeMirror widgets for code fields. """

    class Meta:
        model = Processor
        widgets = {
            'requirements': CodeMirrorTextarea(
                mode='shell',
                addon_js=settings.CODEMIRROR_ADDONS_JS,
                addon_css=settings.CODEMIRROR_ADDONS_CSS,
                keymap=settings.CODEMIRROR_KEYMAP,
            ),
            'accept_code': CodeMirrorTextarea(
                mode='python',
                addon_js=settings.CODEMIRROR_ADDONS_JS,
                addon_css=settings.CODEMIRROR_ADDONS_CSS,
                keymap=settings.CODEMIRROR_KEYMAP,
            ),
            'process_code': CodeMirrorTextarea(
                mode='python',
                addon_js=settings.CODEMIRROR_ADDONS_JS,
                addon_css=settings.CODEMIRROR_ADDONS_CSS,
                keymap=settings.CODEMIRROR_KEYMAP,
            ),
        }


class ProcessorAdmin(admin.ModelAdmin):

    """ Processor admin class. """

    form = ProcessorAdminForm
    list_display = (
        'id', 'name', 'slug',
        'is_active', 'parent',
        'short_description_en',
        'processor_type', 'needs_parameters',
        'user',
    )
    list_display_links = ('id', 'image', 'name', 'slug', )
    list_filter = ('is_active', 'processor_type',
                   'needs_parameters', 'user', )
    ordering = ('name', )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    search_fields = (
        'name', 'url',
        'short_description_en', 'short_description_fr',
    )
    fieldsets = (
        (_(u'Main'), {
            'classes': ('grp-collapse', ),
            'fields': (
                'name',
                ('slug', 'is_active', ),
                ('processor_type', 'needs_parameters', ),
            ),
        }),
        (_(u'Description'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'short_description_en',
                'description_en',

                'short_description_fr',
                'description_fr',

                'short_description_nt',
                'description_nt',
            ),
        }),
        (_(u'Code'), {
            'classes': ('grp-collapse', ),
            'fields': (
                'requirements',
                'accept_code',
                'process_code',
            ),
        }),
        (_(u'Other (internals)'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                ('source_address', 'parent', 'user', ),
                ('duplicate_of', 'duplicate_status', ),
            ),
        }),
    )


# class ProcessingChainAdmin(admin.ModelAdmin):

#     """ Processor admin class. """

#     form = ProcessorAdminForm
#     list_display = (
#         'id', 'name', 'is_active', 'parent',
#         'short_description_en',
#         'processor_type', 'needs_parameters',
#         'user',
#     )
#     list_display_links = ('id', 'image', 'name', 'slug', )
#     list_filter = ('processor_type', 'needs_parameters', 'user', )
#     ordering = ('name', )
#     change_list_template = "admin/change_list_filter_sidebar.html"
#     change_list_filter_template = "admin/filter_listing.html"
#     search_fields = (
#         'name', 'url',
#         'short_description_en', 'short_description_fr',
#     )


class ChainedItemAdmin(admin.ModelAdmin):

    """ Chained item admin class. """

    list_display = (
        'id', 'chain', 'position', 'item',
        'is_valid',
    )
    list_display_links = ('id', 'chain', 'position', )
    list_filter = ('chain', 'is_valid', )
    ordering = ('chain', 'position', )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
