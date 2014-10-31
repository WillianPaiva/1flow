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

from ..models.reldb import (  # NOQA
    UserImport,
)


class UserImportAdmin(admin.ModelAdmin):

    """ UserImport admin class. """

    list_display = (
        'id', 'user',
        'date_started', 'date_finished',
        'status', 'lines',
        'articles_created_count_display',
        'feeds_created_count_display',
        'items_failed_count_display',
    )
    list_display_links = ('id', )
    list_filter = ('status', 'lines', )
    ordering = ('-date_created', 'date_started', )
    date_hierarchy = 'date_created'
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    search_fields = ('urls', 'results', )

    def articles_created_count_display(self, obj):
        """ FILL ME, pep257. """

        try:
            return len(obj.results['created']['articles'])

        except:
            return u'—'

    # articles_created_count_display.allow_tags        = True
    articles_created_count_display.short_description = _(u'Art. created')
    # articles_created_count_display.admin_order_field = 'tags'

    def feeds_created_count_display(self, obj):
        """ FILL ME, pep257. """

        try:
            return len(obj.results['created']['feeds'])

        except:
            return u'—'

    # feeds_created_count_display.allow_tags        = True
    feeds_created_count_display.short_description = _(u'Feeds created')
    # feeds_created_count_display.admin_order_field = 'tags'

    def items_failed_count_display(self, obj):
        """ FILL ME, pep257. """

        try:
            return len(obj.results['failed'])

        except:
            return u'—'

    # items_failed_count_display.allow_tags        = True
    items_failed_count_display.short_description = _(u'Failed')
    # items_failed_count_display.admin_order_field = 'tags'
