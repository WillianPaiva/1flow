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
    WebSite,
)


class WebSiteAdmin(admin.ModelAdmin):

    """ WebSite admin class. """

    list_display = (
        'id', 'image_display', 'name',
        'slug', 'url',
        'fetch_limit_nr',
        'feeds_count_display',
    )
    list_display_links = ('id', 'image', 'name', 'slug', )
    list_filter = ('fetch_limit_nr', )
    ordering = ('name', )
    # date_hierarchy = 'date_created'
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    search_fields = ('name', 'slug', 'url', )

    def image_display(self, obj):
        """ FILL ME, pep257. """

        if obj.image:
            image_url = obj.image.url

        elif obj.image_url:
            image_url = obj.image_url

        else:
            return u'—'

        return (u'<img src="{0}" style="max-width: 48px; max-height: 48px'
                u'"/>').format(image_url)

    image_display.allow_tags        = True
    image_display.short_description = _(u'image')
    # image_display.admin_order_field = 'feeds__count'

    def feeds_count_display(self, obj):
        """ FILL ME, pep257. """

        try:
            return obj.feeds.count()

        except:
            return u'—'

    # feeds_count_display.allow_tags        = True
    feeds_count_display.short_description = _(u'Feeds')
    feeds_count_display.admin_order_field = 'feeds__count'
