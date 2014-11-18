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

from sparks.django.adminfilters import null_filter

from ..models.reldb import (  # NOQA
    CONTENT_TYPES,
    ORIGINS,
    Article,
    OriginalData,
    Language,
)


class ContentTypeListFilter(admin.SimpleListFilter):
    title = _(u'Content type')
    parameter_name = 'content_type'

    def lookups(self, request, model_admin):

        return [(-1, _(u'None'), )] + CONTENT_TYPES.get_choices()

    def queryset(self, request, queryset):

        if self.value() == -1:
            return queryset.filter(content_type=None)

        elif self.value() >= 0:
            return queryset.filter(content_type=self.value())

        return queryset


class OriginListFilter(admin.SimpleListFilter):
    title = _(u'Origin')
    parameter_name = 'origin'

    def lookups(self, request, model_admin):

        return [(-1, _(u'None'), )] + ORIGINS.get_choices()

    def queryset(self, request, queryset):

        if self.value() == -1:
            return queryset.filter(origin=None)

        elif self.value() >= 0:
            return queryset.filter(origin=self.value())

        return queryset


class LanguageListFilter(admin.SimpleListFilter):
    title = _(u'Language')
    parameter_name = 'language_id'

    def lookups(self, request, model_admin):

        return [(-1, _(u'None'), )] + [
            l for l in Language.objects.filter(
                duplicate_of_id=None).values_list('id', 'name')
        ]

    def queryset(self, request, queryset):

        if self.value() == -1:
            return queryset.filter(language_id=None)

        elif self.value():
            return queryset.filter(language_id=self.value())

        return queryset


class ArticleAdmin(admin.ModelAdmin):

    """ Article admin. """

    class Media:
        js = (settings.STATIC_URL + 'writingfield/mousetrap.min.js',
              settings.STATIC_URL + 'writingfield/writingfield.js',)
        css = {
            'all': (
                '//netdna.bootstrapcdn.com/font-awesome/3.2.1/css/font-awesome.css',  # NOQA
                settings.STATIC_URL + 'writingfield/writingfield.css',
                # settings.STATIC_URL + 'admin/admin.css',
            )
        }

    # form = ArticleAdminForm
    list_display = ('id', 'name', 'language', 'url_absolute',
                    'date_published', 'tags_display',
                    'is_orphaned', 'duplicate_of_display',
                    'content_type_display',
                    'content_error_display',
                    'url_error_display', )
    list_display_links = ('id', 'name', )
    date_hierarchy = 'date_created'
    search_fields = ('name', 'slug', )
    ordering = ('-date_published', )
    list_filter = (LanguageListFilter,
                   'is_orphaned', 'url_absolute',
                   null_filter('duplicate_of'),
                   null_filter('url_error'),
                   null_filter('content_error'),
                   'origin',
                   'content_type', )

    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    raw_id_fields = ('tags', 'authors', 'publishers',
                     'sources', 'duplicate_of', 'feeds', )
    fieldsets = (
        ('Main', {
            'fields': (
                'name',
                ('language', 'text_direction', 'content_type', ),
                'content',
                ('word_count', 'tags', 'default_rating'),
                ('authors', 'publishers', ),
            ),
        }),
        ('URL & status', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'url',
                ('url_absolute', 'is_orphaned', 'duplicate_of'),

                # 'date_created' cannot be displayed
                # because it's an auto_now_add field.
                ('date_published', ),
                'url_error',
                'content_error',
            ),
        }),
        ('Other', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'image_url',
                'slug',
                'excerpt',
                ('sources', 'origin', ),
            ),
        }),
    )

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

    def duplicate_of_display(self, obj):
        """ FILL ME, pep257. """

        if obj.duplicate_of:
            return (u'<a href="{0}article/{1}" '
                    u'style="cursor: pointer; font-size: 300%;" '
                    u'target="_blank">∃</a>').format(
                settings.NONREL_ADMIN, obj.duplicate_of_id)

        return u''

    duplicate_of_display.allow_tags        = True
    duplicate_of_display.short_description = _(u'Duplicate of')
    duplicate_of_display.admin_order_field = 'duplicate_of'

    def content_type_display(self, obj):
        """ FILL ME, pep257. """

        if obj.content_type:
            return u'MD' if obj.content_type == CONTENT_TYPES.MARKDOWN else u'…'

        return u''

    content_type_display.allow_tags        = True
    content_type_display.short_description = _(u'Content')
    content_type_display.admin_order_field = 'content_type'

    def content_error_display(self, obj):
        """ FILL ME, pep257. """

        if obj.content_error:
            return _(u'<span title="{0}" '
                     u'style="cursor: pointer; font-size: 300%">'
                     u'•••</span>').format(obj.content_error)

        return u''

    content_error_display.allow_tags        = True
    content_error_display.short_description = _(u'Fetch err.')
    content_error_display.admin_order_field = 'content_error'

    def url_error_display(self, obj):
        """ FILL ME, pep257. """

        if obj.url_error:
            return _(u'<span title="{0}" '
                     u'style="cursor: pointer; font-size: 300%;">'
                     u'•••</span>').format(obj.url_error)

        return u''

    url_error_display.allow_tags        = True
    url_error_display.short_description = _(u'URL err.')
    url_error_display.admin_order_field = 'url_error'
