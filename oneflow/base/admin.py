# -*- coding: utf-8 -*-
"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

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

import csv
import logging

from constance.admin import ConstanceAdmin

from django.conf import settings
from django.http import HttpResponse
from django.template.defaultfilters import slugify
from django.contrib.admin.util import flatten_fieldsets
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User as DjangoUser
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict


from django.contrib import admin

from .models import EmailContent, User

from sparks.django.utils import languages, truncate_field


LOGGER = logging.getLogger(__name__)

# Monkey-patch constance to create nice groups.
ConstanceAdmin.fieldsets = (

        (_(u'Worker control & maintenance mode'), {
            'classes': ('grp-collapse grp-open', ),
            'fields': (
                'FEED_FETCH_DISABLED',
            ),
        }),

        (_(u'User announcements'), {
            'classes': ('grp-collapse grp-open', ),
            'fields': (
                'ANNOUNCEMENT_USER',
                'ANNOUNCEMENT_USER_PREFIX',
                'ANNOUNCEMENT_USER_PRIORITY',
                'ANNOUNCEMENT_USER_START',
                'ANNOUNCEMENT_USER_END',
            ),
        }),
        (_(u'Staff announcements'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'ANNOUNCEMENT_STAFF',
                'ANNOUNCEMENT_STAFF_PREFIX',
                'ANNOUNCEMENT_STAFF_PRIORITY',
                'ANNOUNCEMENT_STAFF_START',
                'ANNOUNCEMENT_STAFF_END',
            ),
        }),

        (_(u'Plain documents'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'DOCUMENTS_ARCHIVING_DISABLED',
            ),
        }),

        (_(u'Reading lists'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'READ_INFINITE_AUTOSCROLL_ENABLED',
                'READ_INFINITE_ITEMS_PER_FETCH',
                'READ_ARTICLE_MIN_LENGTH',
                'READ_AVERAGE_READING_SPEED',
            ),
        }),

        (_(u'RSS feed refreshing'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                # 'FEED_FETCH_DISABLED' is located in “worker control” section
                'FEED_FETCH_GHOST_ENABLED',
                'FEED_FETCH_MAX_ERRORS',
                'FEED_FETCH_DEFAULT_INTERVAL',
                'FEED_FETCH_MIN_INTERVAL',
                'FEED_FETCH_MAX_INTERVAL',
                'FEED_FETCH_RAISE_THRESHOLD',
                'FEED_FETCH_PARALLEL_LIMIT',
                'FEED_REFRESH_RANDOMIZE',
                'FEED_REFRESH_RANDOMIZE_DELAY',
                'FEED_ADMIN_LIST_PER_PAGE',
                'FEED_ADMIN_MEANINGFUL_DELTA',
                'FEED_CLOSED_WARN_LIMIT',
            ),
        }),

        (_(u'Article fetching & parsing'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'ARTICLE_FETCHING_DEBUG',
                'ARTICLE_ABSOLUTIZING_DISABLED',
                'ARTICLE_FETCHING_DISABLED',
                'ARTICLE_FETCHING_TEXT_DISABLED',
                'ARTICLE_FETCHING_VIDEO_DISABLED',
                'ARTICLE_FETCHING_IMAGE_DISABLED',
                'ARTICLE_MARKDOWN_DISABLED',
                'ARTICLE_ARCHIVE_BATCH_SIZE',
                'ARTICLE_ARCHIVE_OLDER_THAN',
                'EXCERPT_PARAGRAPH_MIN_LENGTH',
            ),
        }),

        (_(u'Logins & registration'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'SOCIAL_LOGIN_ENABLED',
                'SOCIAL_REGISTRATION_ENABLED',
                'LOCAL_LOGIN_ENABLED',
                'LOCAL_REGISTRATION_ENABLED',
            ),
        }),

        (_(u'Site theme & CDNs'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'WEB_CDNS_ENABLED',
                'WEB_BOOTSWATCH_THEME',
                'WEB_THEME_NAVBAR_INVERSE',
            ),
        }),


        (_(u'User support'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'SUPPORT_EMAIL_ADDRESS',
                'IRC_SUPPORT_CHANNEL',
                'IRC_SUPPORT_SERVER',
            ),
        }),

        (_(u'Check tasks'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'CHECK_SUBSCRIPTIONS_DISABLED',
                'CHECK_DUPLICATES_DISABLED',
                'CHECK_READS_DISABLED',
            ),
        }),

        (_(u'Dangerous or debug'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'STAFF_HAS_FULL_ACCESS',
            ),
        }),

        (_(u'Google Reader (obsolete)'), {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'GR_MAX_ARTICLES',
                'GR_MAX_FEEDS',
                'GR_LOAD_LIMIT',
                'GR_WAVE_LIMIT',
                'GR_MAX_RETRIES',
                'GR_END_DATE',
                'GR_STORAGE_LIMIT',
            ),
        }),
    )


# •••••••••••••••••••••••••••••••••••••••••••••••• Helpers and abstract classes


class NearlyReadOnlyAdmin(admin.ModelAdmin):
    """ borrowed from https://code.djangoproject.com/ticket/17295
        with enhancements from http://stackoverflow.com/a/12923739/654755 """

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return self.readonly_fields

        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = [field.name for field in self.model._meta.fields]
        return fields

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class CSVAdminMixin(admin.ModelAdmin):
    """
    Adds a CSV export action to an admin view.
    Modified/updated version of http://djangosnippets.org/snippets/2908/

    http://stackoverflow.com/a/16198394/654755 could be a future cool thing
    to implement, to avoid selecting everyone before exporting.
    """

    # This is the maximum number of records that will be written.
    # Exporting massive numbers of records should be done asynchronously.
    # Excel is capped @ 65535 + 1 header line.
    csv_record_limit = 65535
    extra_csv_fields = ()

    def get_actions(self, request):

        try:
            self.actions.append('csv_export')

        except AttributeError:
            self.actions = ('csv_export', )

        actions = super(CSVAdminMixin, self).get_actions(request)

        return actions or SortedDict()

    def get_extra_csv_fields(self, request):
        return self.extra_csv_fields

    def csv_export(self, request, queryset, *args, **kwargs):
        response = HttpResponse(mimetype='text/csv')

        response['Content-Disposition'] = "attachment; filename={}.csv".format(
            slugify(self.model.__name__)
        )

        headers = list(self.list_display) + list(
            self.get_extra_csv_fields(request)
        )

        # BOM (Excel needs it to open UTF-8 file properly)
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.DictWriter(response, headers)

        # Write header.
        header_data = {}
        for name in headers:
            if hasattr(self, name) \
                    and hasattr(getattr(self, name), 'short_description'):
                header_data[name] = getattr(
                    getattr(self, name), 'short_description')

            else:
                field = self.model._meta.get_field_by_name(name)

                if field and field[0].verbose_name:
                    header_data[name] = field[0].verbose_name

                else:
                    header_data[name] = name

            header_data[name] = header_data[name].encode('utf-8', 'ignore')

        writer.writerow(header_data)

        # Write records.
        for row in queryset[:self.csv_record_limit]:
            data = {}
            for name in headers:
                if hasattr(row, name):
                    data[name] = getattr(row, name)
                elif hasattr(self, name):
                    data[name] = getattr(self, name)(row)
                else:
                    raise Exception('Unknown field: %s' % (name,))

                if callable(data[name]):
                    data[name] = data[name]()

                if isinstance(data[name], unicode):
                    data[name] = data[name].encode('utf-8', 'ignore')
                else:
                    data[name] = unicode(data[name]).encode('utf-8', 'ignore')

            writer.writerow(data)

        return response

    csv_export.short_description = _(
        u'Export selected %(verbose_name_plural)s to CSV'
    )


# ••••••••••••••••••••••••••••••••••••••••••••••• Base Django App admin classes


class OneFlowUserAdmin(UserAdmin, CSVAdminMixin):

    list_display = ('id', 'username', 'email', 'full_name_display',
                    'date_joined', 'last_login',
                    'email_announcements',
                    'is_active', 'is_staff', 'is_superuser',
                    'groups_display', )
    list_display_links = ('username', 'email', 'full_name_display', )
    list_filter = ('email_announcements',
                   'is_active', 'is_staff', 'is_superuser', )
    ordering = ('-date_joined',)
    date_hierarchy = 'date_joined'
    search_fields = ('email', 'first_name', 'last_name', )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    # Don't display the UserProfile inline, this will conflict with the
    # post_save() signal in profiles.models. There is a race condition…
    #inlines = [] if UserProfile is None else [UserProfileInline, ]

    def groups_display(self, obj):
        return u', '.join([g.name for g in obj.groups.all()]
                          ) if obj.groups.count() else u'—'

    groups_display.short_description = _(u'Groups')

    def full_name_display(self, obj):
        return obj.get_full_name()

    full_name_display.short_description = _(u'Full name')

admin.site.register(User, OneFlowUserAdmin)

try:
    admin.site.unregister(DjangoUser)
except:
    pass


if settings.FULL_ADMIN:
    subject_fields_names = tuple(('subject_' + code)
                                 for code, lang in languages)
    subject_fields_displays = tuple((field + '_display')
                                    for field in subject_fields_names)

    class EmailContentAdmin(admin.ModelAdmin):
        list_display  = ('name', ) + subject_fields_displays
        search_fields = ('name', ) + subject_fields_names
        ordering      = ('name', )
        save_as       = True

    for attr, attr_name in zip(subject_fields_names,
                               subject_fields_displays):
        setattr(EmailContentAdmin, attr_name,
                truncate_field(EmailContent, attr))

    admin.site.register(EmailContent, EmailContentAdmin)
