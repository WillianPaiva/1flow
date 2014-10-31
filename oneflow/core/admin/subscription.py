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

from constance import config

from django.utils.translation import ugettext_lazy as _  # , pgettext_lazy

from django.contrib import admin

from ..models.reldb import (  # NOQA
    Subscription,
)


class SubscriptionAdmin(admin.ModelAdmin):

    """ Subscription admin. """

    # form = MongoFeedAdminForm
    list_display = (
        'id', 'name',
        'is_internal_display',
        'user', 'feed',
        'feed_items_count_display',
        'reads_count_display',
        'cached_reads_count_display',
    )
    list_display_links = ('id', 'name', )
    list_per_page = config.FEED_ADMIN_LIST_PER_PAGE
    search_fields = (
        'name',
        'feed__name',
        'feed__description_en',
        'feed__description_fr',
        'feed__short_description_en',
        'feed__short_description_fr',

        'feed__website__name',
        'feed__website__url',
        'feed__website__description_en',
        'feed__website__description_fr',
        'feed__website__short_description_en',
        'feed__website__short_description_fr',
    )
    # exclude = ('tags', )
    raw_id_fields = ('user', 'feed', 'reads', 'tags', )
    ordering = ('user__username', 'name', )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    def recent_items_count_display(self, obj):
        """ FILL ME, pep257. """

        return obj.recent_items_count

    recent_items_count_display.short_description = _(u'Recent')
    # recent_items_count_display.admin_order_field = 'recent_items_count'

    def reads_count_display(self, obj):
        """ FILL ME, pep257. """

        return obj.reads.count()

    reads_count_display.short_description = _(u'Reads')
    reads_count_display.admin_order_field = 'reads__count'

    def cached_reads_count_display(self, obj):
        """ FILL ME, pep257. """

        return obj.all_items_count

    cached_reads_count_display.short_description = _(u'Cache')

    def feed_items_count_display(self, obj):
        """ FILL ME, pep257. """

        return obj.feed.items.count()

    feed_items_count_display.short_description = _(u'Feed items')
    feed_items_count_display.admin_order_field = 'feed__items__count'

    def is_internal_display(self, obj):
        """ FILL ME, pep257. """

        return obj.feed.is_internal

    is_internal_display.short_description = _(u'Internal?')
    is_internal_display.admin_order_field = 'feed__is_internal'
    is_internal_display.boolean           = True
