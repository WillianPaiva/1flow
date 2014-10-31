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

from django.conf import settings
from django.utils.translation import ugettext_lazy as _  # , pgettext_lazy

from django.contrib import admin

from ..models.reldb import (  # NOQA
    Read,
)


class ReadAdmin(admin.ModelAdmin):

    """ Read admin. """

    list_display = (
        'id', 'user', 'item', 'is_good',
        'is_read', 'date_read',
        'is_starred', 'date_starred',
        'is_archived', 'date_archived',
        'is_bookmarked', 'date_bookmarked',
        'bookmark_type', 'tags', 'rating',
    )
    list_editable = (
        'is_good',
        'is_read', 'is_starred',
        'is_archived', 'is_bookmarked',
        'bookmark_type', 'rating',
    )
    list_filter = (
        'is_read', 'is_auto_read',
        'is_starred', 'is_bookmarked', 'rating',
    )
    search_fields = (
        'item__name',
        'item__excerpt',
        'user__username',
        'user__firstname',
        'user__lastname',
    )
    list_display_links = ('id', 'user', 'item', )
    date_hierarchy = 'date_created'
    ordering = ('-date_created', )
    raw_id_fields = ('item', 'user', 'senders', 'tags', 'subscriptions', )

    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    def tags_display(self, obj):
        """ FILL ME, pep257. """

        try:
            return u', '.join(u'<a href="{0}tag/{1}" '
                              u'target="_blank">{2}</a>'.format(
                                  settings.NONREL_ADMIN,
                                  tag.id, tag.name)
                              for tag in obj.tags.all())
        except Exception as e:
            return unicode(e)

    tags_display.allow_tags        = True
    tags_display.short_description = _(u'Tags')
    tags_display.admin_order_field = 'tags'
