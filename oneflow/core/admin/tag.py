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

from mptt.admin import MPTTModelAdmin

from ..models.reldb import (  # NOQA
    SimpleTag as Tag,
)


class TagAdmin(MPTTModelAdmin):

    """ Tag admin class. """

    list_display = ('id', 'name', )
    list_display_links = ('id', 'name', )
    # list_filter = ('parent', )
    ordering = ('name', 'parent', )
    # date_hierarchy = 'date_joined'
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    search_fields = ('name', )
