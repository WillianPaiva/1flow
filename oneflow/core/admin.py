# -*- coding: utf-8 -*-
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

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

import dateutil.parser

from humanize.i18n import django_language

from constance import config
from django.forms import TextInput, CheckboxSelectMultiple
from django.conf import settings
from django.utils.translation import ugettext_lazy as _  # , pgettext_lazy
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
#from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse

#from django_markdown.widgets import MarkdownWidget
from writingfield import FullScreenTextarea

from .models.nonrel import (Tag, Feed, Article, Read, CONTENT_TYPE_MARKDOWN,
                            User as MongoUser, Group as MongoGroup)
from .models.reldb import HelpContent, MailAccount, MailFeed, MailFeedRule
from django.contrib import admin
import mongoadmin
from mongodbforms import DocumentForm

from sparks.django.utils import languages, truncate_field

#from ..base.admin import CSVAdminMixin
from ..base.utils.dateutils import naturaldelta, naturaltime

# NOTE: using "from base.models import User" will generate
# a "cannot proxy swapped model base.User" when creating the
# GriUser class. Using `get_user_model()` works and is the
# Django recommended way of doing it.
User = get_user_model()


if settings.FULL_ADMIN:
    name_fields_names = tuple(('name_' + code)
                              for code, lang in languages)
    name_fields_displays = tuple((field + '_display')
                                 for field in name_fields_names)
    content_fields_names = tuple(('content_' + code)
                                 for code, lang in languages)
    content_fields_displays = tuple((field + '_display')
                                    for field in content_fields_names)

    class HelpContentAdmin(admin.ModelAdmin):
        list_display_links = ('label', )
        list_display       = ('label', 'ordering', 'active', ) \
            + name_fields_displays
        list_editable      = ('ordering', 'active', )
        search_fields      = ('label', ) + name_fields_names + content_fields_names # NOQA
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

    admin.site.register(HelpContent, HelpContentAdmin)


# ————————————————————————————————————————————————————————————————————— MongoDB


class TagAdmin(mongoadmin.DocumentAdmin):

    list_display = ('id', 'name', 'language', 'duplicate_of',
                    'parents_display', 'children_display')
    list_display_links = ('id', 'name', )
    #list_editable = ('language', )
    search_fields = ('name', 'slug', )
    change_list_filter_template = "admin/filter_listing.html"
    filter_horizontal = ('parents', 'children', )

    def change_view(self, request, object_id, extra_context=None):
        self.exclude = ('origin', )  # 'parents', 'children', )

        return super(TagAdmin, self).change_view(request, object_id,
                                                 extra_context=None)

    def parents_display(self, obj):

        if obj.parents:
            return u', '.join(u'<a href="{0}tag/{1}" '
                              u'target="_blank">{2}</a>'.format(
                                  settings.NONREL_ADMIN,
                                  parent.id, parent.name)
                              for parent in obj.parents)

        return u'—'

    parents_display.short_description = _(u'Parents')
    parents_display.allow_tags = True

    def children_display(self, obj):

        if obj.children:
            return u', '.join(u'<a href="{0}tag/{1}" '
                              u'target="_blank">{2}</a>'.format(
                                  settings.NONREL_ADMIN,
                                  child.id, child.name)
                              for child in obj.children)

        return u'—'

    children_display.short_description = _(u'Children')
    children_display.allow_tags = True


admin.site.register(Tag, TagAdmin)


class MongoUserAdminForm(DocumentForm):
    class Meta:
        model = MongoUser
        widgets = {
            'username': TextInput(attrs={'class': 'vURLField'}),
            'first_name': TextInput(attrs={'class': 'vURLField'}),
            'last_name': TextInput(attrs={'class': 'vURLField'}),
        }


class MongoUserAdmin(mongoadmin.DocumentAdmin):
    list_display = ('id', 'username', 'first_name', 'last_name', 'django_user',
                    'is_staff_display', 'is_superuser_display', )
    list_display_links = ('id', 'username', )
    search_fields = ('username', 'first_name', 'last_name', )
    change_list_filter_template = "admin/filter_listing.html"
    #filter_horizontal = ('parents', 'children', )
    form = MongoUserAdminForm
    # raw_id_fields = ()
    fieldsets = (
        ('Main', {
            'fields': (
                'username',
                ('first_name', 'last_name', ),
                ('is_staff', 'is_superuser', 'django_user', ),
                #'permissions'
            ),
        }),
        ('Friends', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'address_book',
            ),
        }),
    )

    def is_staff_display(self, obj):

        return obj.is_staff

    is_staff_display.short_description = _(u'Staff?')
    is_staff_display.admin_order_field = 'is_staff'
    is_staff_display.boolean = True

    def is_superuser_display(self, obj):

        return obj.is_superuser

    is_superuser_display.short_description = _(u'Superuser?')
    is_superuser_display.admin_order_field = 'is_superuser'
    is_superuser_display.boolean = True


admin.site.register(MongoUser, MongoUserAdmin)


class MongoGroupAdminForm(DocumentForm):
    class Meta:
        model = MongoGroup
        exclude = ('backend', )
        widgets = {
            'name': TextInput(attrs={'class': 'vURLField'}),
            'internal_name': TextInput(attrs={'class': 'vURLField'}),
        }


class MongoGroupAdmin(mongoadmin.DocumentAdmin):
    list_display = ('id', 'name', 'internal_name', 'creator',
                    'backend', )
    list_display_links = ('id', 'name',  'internal_name', )
    search_fields = ('name', 'internal_name', )
    change_list_filter_template = "admin/filter_listing.html"
    #filter_horizontal = ('parents', 'children', )
    form = MongoGroupAdminForm
    raw_id_fields = ('members', 'administrators', 'guests', )
    fieldsets = (
        ('Main', {
            'fields': (
                ('name', 'internal_name', ),
            ),
        }),
        ('Members', {
            'fields': (
                'members',
            ),
        }),
        ('Administrators', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'administrators',
            ),
        }),
        ('Guests', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'guests',
            ),
        }),
    )


admin.site.register(MongoGroup, MongoGroupAdmin)


class ArticleAdminForm(DocumentForm):
    class Meta:
        model = Article
        widgets = {
            'image_url': TextInput(attrs={'class': 'vURLField'}),
            #'content': MarkdownWidget(attrs={'class': 'markdown-editor'}),
            'content': FullScreenTextarea(),
            'url_error': TextInput(attrs={'class': 'vURLField'}),
            'content_error': TextInput(attrs={'class': 'vURLField'}),
        }


class ArticleAdmin(mongoadmin.DocumentAdmin):

    class Media:
        js = (settings.STATIC_URL + 'writingfield/mousetrap.min.js',
              settings.STATIC_URL + 'writingfield/writingfield.js',)
        css = {
            'all': (
                '//netdna.bootstrapcdn.com/font-awesome/3.2.1/css/font-awesome.css', # NOQA
                settings.STATIC_URL + 'writingfield/writingfield.css',
                # settings.STATIC_URL + 'admin/admin.css',
            )
        }

    form = ArticleAdminForm
    list_display = ('id', 'title', 'language', 'url_absolute',
                    'date_published', 'tags_display',
                    'orphaned', 'duplicate_of_display',
                    'content_type_display',
                    'content_error_display',
                    'url_error_display', )
    list_display_links = ('id', 'title', )
    search_fields = ('title', 'slug', )
    change_list_filter_template = "admin/filter_listing.html"
    raw_id_fields = ('tags', 'authors', 'publishers',
                     'source', 'duplicate_of', 'feeds', )
    fieldsets = (
        ('Main', {
            'fields': (
                'title',
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
                ('url_absolute', 'orphaned', 'duplicate_of'),
                ('date_added', 'date_published', ),
                'url_error',
                'content_error',
            ),
        }),
        ('Other', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                'image_url',
                'slug', 'pages_urls',
                'excerpt',
                ('source', 'origin_type', 'comments_feed'),
            ),
        }),
    )

    def tags_display(self, obj):

        try:
            return u', '.join(u'<a href="{0}tag/{1}" '
                              u'target="_blank">{2}</a>'.format(
                                  settings.NONREL_ADMIN,
                                  tag.id, tag.name)
                              for tag in obj.tags)
        except Exception, e:
            return unicode(e)

    tags_display.allow_tags        = True
    tags_display.short_description = _(u'Tags')
    tags_display.admin_order_field = 'tags'

    def duplicate_of_display(self, obj):

        if obj.duplicate_of:
            return (u'<a href="{0}article/{1}" '
                    u'style="cursor: pointer; font-size: 300%;" '
                    u'target="_blank">∃</a>').format(
                settings.NONREL_ADMIN, obj.duplicate_of.id)

        return u''

    duplicate_of_display.allow_tags        = True
    duplicate_of_display.short_description = _(u'Duplicate of')
    duplicate_of_display.admin_order_field = 'duplicate_of'

    def content_type_display(self, obj):

        if obj.content_type:
            return u'MD' if obj.content_type == CONTENT_TYPE_MARKDOWN else u'…'

        return u''

    content_type_display.allow_tags        = True
    content_type_display.short_description = _(u'Content')
    content_type_display.admin_order_field = 'content_type'

    def content_error_display(self, obj):

        if obj.content_error:
            return _(u'<span title="{0}" '
                     u'style="cursor: pointer; font-size: 300%">'
                     u'•••</span>').format(obj.content_error)

        return u''

    content_error_display.allow_tags        = True
    content_error_display.short_description = _(u'Fetch err.')
    content_error_display.admin_order_field = 'content_error'

    def url_error_display(self, obj):

        if obj.url_error:
            return _(u'<span title="{0}" '
                     u'style="cursor: pointer; font-size: 300%;">'
                     u'•••</span>').format(obj.url_error)

        return u''

    url_error_display.allow_tags        = True
    url_error_display.short_description = _(u'URL err.')
    url_error_display.admin_order_field = 'url_error'


admin.site.register(Article, ArticleAdmin)


class ReadAdmin(mongoadmin.DocumentAdmin):

    list_display = ('id', 'article_display',
                    'user_display',
                    'subscriptions_display',
                    'date_created', 'is_good',
                    'is_read', 'date_read',
                    'is_auto_read', 'date_auto_read', )
    list_display_links = ('id', )
    change_list_filter_template = "admin/filter_listing.html"
    raw_id_fields = ('article', 'user', 'subscriptions', )
    fieldsets = (
        ('Main', {
            'fields': (
                'article',
                ('user', 'tags', ),
                ('is_good', 'date_created', 'rating', ),
                ('is_read', 'date_read', ),
                ('is_starred', 'date_starred', ),
                ('is_archived', 'date_archived', ),
                ('is_bookmarked', 'date_bookmarked', 'bookmark_type'),
                ('is_auto_read', 'date_auto_read', ),
            ),
        }),
        ('Watch attributes', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                ('is_fact', 'date_fact', ),
                ('is_number', 'date_number', ),
                ('is_quote', 'date_quote', ),
                ('is_prospective', 'date_prospective', ),
                ('is_rules', 'date_rules', ),
                ('is_analysis', 'date_analysis', ),
                ('is_knowhow', 'date_knowhow', ),
                ('is_knowledge', 'date_knowledge', 'knowledge_type', ),
                ('is_fun', 'date_fun', ),
            ),
        }),
    )

    def user_display(self, obj):

        try:
            return u'<a href="{0}user/{1}" target="_blank">{2}</a>'.format(
                settings.NONREL_ADMIN, obj.user.id, obj.user.username)

        except Exception, e:
            return unicode(e)

    user_display.allow_tags        = True
    user_display.short_description = _(u'User')
    user_display.admin_order_field = 'user'

    def article_display(self, obj):

        art = obj.article

        try:
            return u'<a href="{0}article/{1}" target="_blank">{2}</a>'.format(
                settings.NONREL_ADMIN, art.id,
                art.title[:40] + (art.title[:40] and u'…'))

        except Exception, e:
            return unicode(e)

    article_display.allow_tags        = True
    article_display.short_description = _(u'Article')
    article_display.admin_order_field = 'article'

    def subscriptions_display(self, obj):

        try:
            return u', '.join(u'<a href="{0}subscription/{1}" '
                              u'target="_blank">{2}</a>'.format(
                                  settings.NONREL_ADMIN,
                                  sub.id, sub.name)
                              for sub in obj.subscriptions)
        except Exception, e:
            return unicode(e)

    subscriptions_display.allow_tags        = True
    subscriptions_display.short_description = _(u'Subscriptions')
    subscriptions_display.admin_order_field = 'subscriptions'


admin.site.register(Read, ReadAdmin)


class HorizontalCheckbox(CheckboxSelectMultiple):
    def render(self, *args, **kwargs):
        output = super(HorizontalCheckbox,
                       self).render(*args, **kwargs)

        return mark_safe(output.replace(
                         u'<ul>', u'').replace(
                         u'</ul>', u'').replace(
                         u'<li>', u'<span style="margin-right:20px">').replace(
                         u'</li>', u'</span>'))


class FeedAdminForm(DocumentForm):
    class Meta:
        model = Feed
        widgets = {
            'url': TextInput(attrs={'class': 'vURLField'}),
            'name': TextInput(attrs={'class': 'vLargeTextField'}),
            'site_url': TextInput(attrs={'class': 'vLargeTextField'}),
            'languages': HorizontalCheckbox(),
            'last_etag': TextInput(attrs={'class': 'vLargeTextField'}),
            'last_modified': TextInput(attrs={'class': 'vLargeTextField'}),
        }


class FeedAdmin(mongoadmin.DocumentAdmin):
    class Media:
        css = {
            'all': (
                '//netdna.bootstrapcdn.com/font-awesome/4.0.0/css/font-awesome.min.css',  # NOQA
            )
        }

    form = FeedAdminForm
    list_display = ('id_display', 'name', 'url_display',
                    'good_for_use_display', 'restricted_display',
                    'is_internal_display',
                    'duplicate_of_display', 'errors_display',
                    'closed_display', 'fetch_interval_display',
                    'last_fetch_display',
                    'date_added_display', 'latest_article_display',
                    'recent_articles_count_display',
                    'all_articles_count_display',
                    'subscriptions_count_display', )

    # Doesn't work with mongoadmin yet
    #list_editable      = ('good_for_use', )

    list_display_links = ('name', )
    list_per_page = config.FEED_ADMIN_LIST_PER_PAGE
    search_fields = ('name', 'url', 'site_url', 'closed', )
    exclude = ('tags', )
    raw_id_fields = ('duplicate_of', 'created_by', )
    # Setting this makes the whole thing unsortable…
    #ordering = ('-last_fetch', )

    # The following fields don't work with mongoadmin.
    #
    #list_filter = ('closed', 'last_fetch', 'recent_articles__count', )
    #date_hierarchy = 'date_added'
    #change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    fieldsets = (
        ('Main', {
            'fields': (('name', 'site_url', ),
                       'thumbnail_url',
                       ('good_for_use', 'restricted', 'is_internal', ),
                       'languages',
                       'description_en', 'description_fr',
                       'notes', ),
        }),
        ('Fetch parameters', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': ('url', 'fetch_interval', 'last_fetch',
                       ('last_etag', 'last_modified',), ),
        }),
        ('Birth & Death', {
            'classes': ('grp-collapse grp-closed', ),
            'fields': (
                ('date_added', 'created_by'),
                ('closed', 'date_closed', ),
                'closed_reason', 'errors',
            ),
        }),
    )
    # def name_display(self, obj):

    #     return u'<a href="{0}" target="_blank" {2}>{1}</a>'.format(
    #         obj.site_url, obj.name, u'style="text-decoration: line-through;"'
    #         if obj.closed else '')

    # name_display.short_description = _(u'Feed name')
    # name_display.allow_tags = True
    # name_display.admin_order_field = 'name'

    def id_display(self, obj):

        return (u'<a href="{0}feed/{1}" target="_blank" title="{1}"><i '
                u'class="fa fa-barcode fa-2x"></i></a>').format(
                    settings.NONREL_ADMIN, obj.id)

    id_display.short_description = _(u'ID')
    id_display.allow_tags = True
    id_display.admin_order_field = 'id'

    def url_display(self, obj):

        return (u'<a href="{0}" target="_blank" {2}>'
                u'<i class="fa fa-rss-square fa-lg fa-fw"></i></a>&nbsp;'
                u'<a href="{1}" target="_blank" {1}>'
                u'<i class="fa fa-globe fa-lg fa-fw"></i></a>'.format(
                    obj.url, obj.site_url,
                    u'style="opacity: 0.5"' if obj.closed else u''))

    url_display.short_description = _(u'URLs')
    url_display.allow_tags = True
    url_display.admin_order_field = 'url'

    def duplicate_of_display(self, obj):

        if obj.duplicate_of:
            return (u'<a href="{0}feed/{1}" target="_blank"><i '
                    u'class="fa fa-link fa-2x fa-rotate-90"></i></a>').format(
                        settings.NONREL_ADMIN, obj.duplicate_of.id)

        return u''

    duplicate_of_display.allow_tags        = True
    duplicate_of_display.short_description = _(u'Dupe of')
    duplicate_of_display.admin_order_field = 'duplicate_of'

    def errors_display(self, obj):

        if obj.closed:
            return u'—'

        if obj.errors:
            last3 = [z.rsplit('@@', 1) for z in obj.errors[:3]]

            with django_language():
                return _(u'<span title="Last 3 errors:\n{0}" '
                         u'style="cursor: pointer">'
                         u'{1} error(s)</span>').format(u'\n'.join(
                                _(u'{0}: {1}').format(naturaltime(
                                    dateutil.parser.parse(y)), x)
                                for x, y in last3), len(obj.errors))

        return u'—'

    errors_display.short_description = _(u'Errors')
    errors_display.allow_tags = True
    errors_display.admin_order_field = 'errors'

    def restricted_display(self, obj):

        return obj.restricted

    restricted_display.short_description = _(u'Restr.?')
    restricted_display.admin_order_field = 'restricted'
    restricted_display.boolean = True

    def is_internal_display(self, obj):

        return obj.restricted

    is_internal_display.short_description = _(u'Sys?')
    is_internal_display.admin_order_field = 'is_internal'
    is_internal_display.boolean = True

    def good_for_use_display(self, obj):

        return obj.good_for_use

    good_for_use_display.short_description = _(u'Shown?')
    good_for_use_display.admin_order_field = 'good_for_use'
    good_for_use_display.boolean = True

    def recent_articles_count_display(self, obj):

        return obj.recent_articles_count

    recent_articles_count_display.short_description = _(u'Recent')
    #recent_articles_count_display.admin_order_field = 'recent_articles_count'

    def all_articles_count_display(self, obj):

        return obj.all_articles_count

    all_articles_count_display.short_description = _(u'Total')
    #all_articles_count_display.admin_order_field = 'all_articles_count'

    def latest_article_display(self, obj):

        if obj.closed:
            return u'—'

        with django_language():
            return naturaltime(obj.latest_article_date_published)

    latest_article_display.short_description = _(u'Latest')
    #latest_article_display.admin_order_field = 'latest_article_date_published'

    def date_added_display(self, obj):

        with django_language():
            return naturaltime(obj.date_added)

    date_added_display.short_description = _(u'Added')
    date_added_display.admin_order_field = 'date_added'

    def fetch_interval_display(self, obj):

        if obj.closed:
            return u'—'

        with django_language():
            return naturaldelta(obj.fetch_interval)

    fetch_interval_display.short_description = _(u'Interval')
    fetch_interval_display.admin_order_field = 'fetch_interval'

    def last_fetch_display(self, obj):

        if obj.closed:
            return u'—'

        if obj.last_fetch is None:
            return _(u'never')

        with django_language():
            return naturaltime(obj.last_fetch)

    last_fetch_display.short_description = _(u'Refreshed')
    last_fetch_display.admin_order_field = 'last_fetch'

    def subscriptions_count_display(self, obj):

        return obj.subscriptions_count

    subscriptions_count_display.short_description = _(u'Subs.')
    #subscriptions_count_display.admin_order_field = 'subscriptions_count'

    def closed_display(self, obj):

        #
        # NOTE: using "fa-spin" on open feeds brings firefox to 100% CPU.
        #

        return (u'<a title="{2}" href="{0}"><i class="fa {1}">'
                u'</i></a>').format(reverse('feed_closed_toggle',
                                            kwargs={'feed_id': obj.id}),
                                    u'fa-power-off fa-lg'
                                    if obj.closed else u'fa-refresh fa-2x',
                                    u'Closed on {0} because of: {1}'.format(
                                        obj.date_closed,
                                        obj.closed_reason) if obj.closed
                                    else _(u'The feed is open'))

    closed_display.short_description = _(u'Run?')
    closed_display.allow_tags = True
    closed_display.admin_order_field = 'closed'


admin.site.register(Feed, FeedAdmin)

admin.site.register(MailAccount)
admin.site.register(MailFeed)
admin.site.register(MailFeedRule)
