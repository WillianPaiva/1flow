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
import json
import dateutil.parser

from humanize.i18n import django_language

from constance import config

from django.conf import settings
from django.utils.translation import ugettext_lazy as _  # , pgettext_lazy
from django.core.urlresolvers import reverse

from django.contrib import admin


# from ..base.admin import CSVAdminMixin
from oneflow.base.utils.dateutils import naturaldelta, naturaltime


from ..models.reldb import (  # NOQA
    # DjangoUser as User,

    BaseFeed,
    RssAtomFeed,

    MailFeed, MailFeedRule,


)


class RssAtomFeedAdmin(admin.ModelAdmin):

    """ RSS/Atom Feed admin. """

    class Media:
        css = {
            'all': (
                '//netdna.bootstrapcdn.com/font-awesome/4.0.0/css/font-awesome.min.css',  # NOQA
            )
        }

    # form = MongoFeedAdminForm
    list_display = ('id', 'name', 'url_display',
                    'is_good', 'is_restricted', 'is_internal',
                    # 'duplicate_of_display',
                    'errors_display',
                    'is_active_display',
                    'fetch_interval_display',
                    'date_last_fetch_display',
                    'date_created_display',
                    'latest_item_display',
                    'recent_items_count_display',
                    'items_count_display',
                    'subscriptions_count_display', )

    list_display_links = ('id', 'name', )
    list_editable      = ('is_good', )
    list_per_page = config.FEED_ADMIN_LIST_PER_PAGE
    search_fields = (
        'name', 'url', 'is_active',
        'description_en',
        'description_fr',
        'short_description_en',
        'short_description_fr',

        'website__name', 'website__url',
        'website__description_en',
        'website__description_fr',
        'website__short_description_en',
        'website__short_description_fr',
    )
    # exclude = ('tags', )
    raw_id_fields = ('duplicate_of', 'user', )
    ordering = ('-date_last_fetch', )
    list_filter = ('is_active', 'date_last_fetch', )
    date_hierarchy = 'date_created'
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    fieldsets = (
        ('Main', {
            'fields': (('name', 'website', 'user', ),
                       'thumbnail',
                       'thumbnail_url',
                       ('is_good', 'is_restricted', 'is_internal', ),
                       'languages',
                       'description_en', 'description_fr',
                       'notes', ),
        }),
        ('Fetch parameters', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': ('url', 'fetch_interval', 'date_last_fetch',
                       ('last_etag', 'last_modified',), ),
        }),
        ('Birth & Death', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                # date_created won't show, never.
                # Cf. http://stackoverflow.com/a/23768545/654755
                # ('date_created', 'user', ),
                ('is_active', 'date_closed', ),
                'closed_reason', 'errors',
            ),
        }),
    )

    def url_display(self, obj):
        """ FILL ME, pep257. """

        return (u'<a href="{0}" target="_blank" {2}>'
                u'<i class="fa fa-rss-square fa-lg fa-fw"></i></a>&nbsp;'
                u'<a href="{1}" target="_blank" {1}>'
                u'<i class="fa fa-globe fa-lg fa-fw"></i></a>'.format(
                    obj.url, obj.website.url if obj.website else u'',
                    u'' if obj.is_active else u'style="opacity: 0.5"'))

    url_display.short_description = _(u'URLs')
    url_display.allow_tags = True
    url_display.admin_order_field = 'url'

    def duplicate_of_display(self, obj):
        """ FILL ME, pep257. """

        if obj.duplicate_of:
            return (u'<a href="{0}feed/{1}" target="_blank"><i '
                    u'class="fa fa-link fa-2x fa-rotate-90"></i></a>').format(
                        settings.NONREL_ADMIN, obj.duplicate_of.id)

        return u''

    duplicate_of_display.allow_tags        = True
    duplicate_of_display.short_description = _(u'Dupe of')
    duplicate_of_display.admin_order_field = 'duplicate_of'

    def errors_display(self, obj):
        """ FILL ME, pep257. """

        if obj.errors:

            errors = json.loads(obj.errors)

            last3 = [z.rsplit('@@', 1) for z in errors[:3]]

            with django_language():
                return _(u'<span title="Last 3 errors:\n{0}" '
                         u'style="cursor: pointer">'
                         u'{1} error(s)</span>').format(
                             u'\n'.join(
                                 _(u'{0}: {1}').format(
                                     naturaltime(dateutil.parser.parse(y)), x)
                                 for x, y in last3), len(errors))

        return u'—'

    errors_display.short_description = _(u'Errors')
    errors_display.allow_tags = True
    errors_display.admin_order_field = 'errors'

    def recent_items_count_display(self, obj):
        """ FILL ME, pep257. """

        return obj.recent_items_count

    recent_items_count_display.short_description = _(u'Recent')
    # recent_items_count_display.admin_order_field = 'recent_items_count'

    def items_count_display(self, obj):
        """ FILL ME, pep257. """

        return u'%s/%s' % (
            obj.items.count(),
            obj.all_items_count
        )

    items_count_display.short_description = _(u'Total')
    items_count_display.admin_order_field = 'items__count'

    def latest_item_display(self, obj):
        """ FILL ME, pep257. """

        if obj.is_active:
            with django_language():
                return naturaltime(obj.latest_item_date_published)

        return u'—'

    latest_item_display.short_description = _(u'Latest')
    # latest_item_display.admin_order_field = 'latest_item_date_published'

    def date_created_display(self, obj):
        """ FILL ME, pep257. """

        with django_language():
            return naturaltime(obj.date_created)

    date_created_display.short_description = _(u'Created')
    date_created_display.admin_order_field = 'date_created'

    def fetch_interval_display(self, obj):
        """ FILL ME, pep257. """

        if obj.is_active:
            with django_language():
                return naturaldelta(obj.fetch_interval)

        return u'—'

    fetch_interval_display.short_description = _(u'Interval')
    fetch_interval_display.admin_order_field = 'fetch_interval'

    def date_last_fetch_display(self, obj):
        """ FILL ME, pep257. """

        if obj.is_active:

            if obj.date_last_fetch is None:
                return _(u'never')

            with django_language():
                return naturaltime(obj.date_last_fetch)

        return u'—'

    date_last_fetch_display.short_description = _(u'Refreshed')
    date_last_fetch_display.admin_order_field = 'date_last_fetch'

    def subscriptions_count_display(self, obj):
        """ FILL ME, pep257. """

        return obj.subscriptions.count()

    subscriptions_count_display.short_description = _(u'Subs.')
    subscriptions_count_display.admin_order_field = 'subscriptions__count'

    def is_active_display(self, obj):
        """ FILL ME, pep257. """

        #
        # NOTE: using "fa-spin" on open feeds brings firefox to 100% CPU.
        #

        return (u'<a title="{2}" href="{0}"><i class="fa {1}">'
                u'</i></a>').format(reverse('feed_closed_toggle',
                                            kwargs={'feed_id': obj.id}),
                                    u'fa-refresh fa-2x'
                                    if obj.is_active else u'fa-power-off fa-lg',
                                    _(u'The feed is open') if obj.is_active
                                    else
                                    u'Closed on {0} because of: {1}'.format(
                                        obj.date_closed,
                                        obj.closed_reason))

    is_active_display.short_description = _(u'Active?')
    is_active_display.allow_tags = True
    is_active_display.admin_order_field = 'is_active'


class MailFeedRuleAdmin(admin.ModelAdmin):

    """ MailFeedRule admin class. """

    list_display = ('id', 'get_mailfeed__name', 'get_mailfeed__user',
                    'group', 'header_field', 'match_type', 'match_value', )
    list_display_links = ('id', 'get_mailfeed__name',
                          'get_mailfeed__user', 'group', )
    list_filter = ('group', )
    # ordering = ('name', 'parent', )
    # date_hierarchy = 'date_joined'
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    # Don't display the UserProfile inline, this will conflict with the
    # post_save() signal in profiles.models. There is a race condition…
    # inlines = [] if UserProfile is None else [UserProfileInline, ]

    def get_mailfeed__name(self, obj):
        """ FILL ME, pep257. """

        return obj.mailfeed.name

    get_mailfeed__name.short_description = _(u'Mail feed')
    get_mailfeed__name.admin_order_field = 'mailfeed__name'

    def get_mailfeed__user(self, obj):
        """ FILL ME, pep257. """

        return obj.mailfeed.user.username

    get_mailfeed__user.short_description = _(u'User')
    get_mailfeed__user.admin_order_field = 'mailfeed__user__username'
