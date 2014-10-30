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

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _  # , pgettext_lazy

from sparks.django.utils import languages, truncate_field

from ..models.reldb import HelpContent


name_fields_names = tuple(('name_' + code)
                          for code, lang in languages)
name_fields_displays = tuple((field + '_display')
                             for field in name_fields_names)
content_fields_names = tuple(('content_' + code)
                             for code, lang in languages)
content_fields_displays = tuple((field + '_display')
                                for field in content_fields_names)


class HelpContentAdmin(admin.ModelAdmin):

    """ Help content admin. """

    list_display_links = ('label', )
    list_display       = ('label', 'ordering', 'active', ) \
        + name_fields_displays
    list_editable      = ('ordering', 'active', )
    search_fields      = ('label', ) + name_fields_names + content_fields_names  # NOQA
    ordering           = ('ordering', 'label', )
    save_as            = True
    fieldsets = (
        (_(u'Main'), {
            'fields': (
                ('label', 'active', 'ordering', ),
            ),
        }),
        (_(u'Translators notes'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'name_nt',
                'content_nt',
            )
        }),
        (_(u'Contents (English)'), {
            'fields': (
                'name_en',
                'content_en',
            )
        }),
        (_(u'Contents (French)'), {
            'fields': (
                'name_fr',
                'content_fr',
            )
        }),
    )

for attr, attr_name in zip(name_fields_names,
                           name_fields_displays):
    setattr(HelpContentAdmin, attr_name,
            truncate_field(HelpContent, attr))

for attr, attr_name in zip(content_fields_names,
                           content_fields_displays):
    setattr(HelpContentAdmin, attr_name,
            truncate_field(HelpContent, attr))
