# -*- coding: utf-8 -*-

import dateutil.parser

from humanize.i18n import django_language

from constance import config
from django.forms import TextInput, CheckboxSelectMultiple
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as _p
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse

from .models.nonrel import Tag, Feed, Article, CONTENT_TYPE_MARKDOWN
from .models.reldb import HelpContent

from django.contrib import admin as django_admin
import mongoadmin as admin
from mongodbforms import DocumentForm

from sparks.django.admin import languages, truncate_field

from ..base.admin import CSVAdminMixin
from ..base.utils.dateutils import now, naturaldelta, naturaltime

from .gr_import import GoogleReaderImport

# NOTE: using "from base.models import User" will generate
# a "cannot proxy swapped model base.User" when creating the
# GriUser class. Using `get_user_model()` works.
User = get_user_model()


class GriUser(User):
    """ Just a proxy to User model, to be able to build a list against it. """

    class Meta:
        proxy = True
        #fields = ('id', 'username', )
        verbose_name = _(u'Google Reader import')
        verbose_name_plural = _(u'Google Reader imports')


class GriOneFlowUserAdmin(UserAdmin, CSVAdminMixin):
    """ Wrap our GoogleReaderImport class onto User accounts,
        to be able to act on imports from the Django administration. """

    list_display = ('id', 'username', 'gri_feeds_display',
                    'gri_articles_display', 'gri_reads_display',
                    'gri_starred_display', 'gri_executed_display',
                    'gri_duration_display', 'gri_eta_display',
                    'gri_action_display', 'can_import_display', )
    list_display_links = ('id', 'username', )
    ordering = ('-date_joined', )
    date_hierarchy = 'date_joined'
    search_fields = ('username', 'email', )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

    def has_add_permission(self, request):
        # Don't display the ADD button in the Django interface.
        return False

    def gri_articles_display(self, obj):

        return GoogleReaderImport(obj.id).articles() or u'—'

    gri_articles_display.short_description = _(u'articles')

    def gri_feeds_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        number, total = gri.feeds(), gri.total_feeds()

        if number >= total:
            return number or u'—'

        return u'%s/%s' % (number, total)

    gri_feeds_display.short_description = _(u'feeds')

    def gri_reads_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        number, total = gri.reads(), gri.total_reads()

        if number >= total:
            return number or u'—'

        return u'%s/%s' % (number, total)

    gri_reads_display.short_description = _p(u'noun, plural', u'reads')

    def gri_starred_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        number, total = gri.starred(), gri.total_starred()

        if number >= total:
            return number or u'—'

        return u'%s/%s' % (number, total)

    gri_starred_display.short_description = _(u'starred')

    def gri_executed_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        with django_language():
            if gri.running() is None:
                return u'—'

            else:
                return naturaltime(gri.start())

    gri_executed_display.short_description = _(u'executed')

    def gri_duration_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        with django_language():
            if gri.running():
                return naturaldelta(now() - gri.start())

            elif gri.running() is False:
                return naturaldelta(gri.end() - gri.start())

            else:
                return u'—'

    gri_duration_display.short_description = _(u'duration')

    def gri_eta_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        eta = gri.eta()

        if eta:
            with django_language():
                return naturaldelta(eta)

        return u'—'

    gri_eta_display.short_description = _(u'ETA')

    def gri_action_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        has_google = obj.social_auth.filter(provider=
                                            'google-oauth2').count() > 0
        if has_google:
            if gri.running():
                return u'<a href="{0}">{1}</a>'.format(
                    reverse('google_reader_import_stop',
                            kwargs={'user_id': obj.id}), _(u'stop'))

            else:
                return u'<a href="{0}">{1}</a>'.format(
                    reverse('google_reader_import',
                            kwargs={'user_id': obj.id}),
                            _(u'start') if gri.running() is None
                            else _(u'restart'))
        else:
            return u'<span style="text-decoration: line-through">OAuth2</span>'

    gri_action_display.short_description = _(u'import')
    gri_action_display.allow_tags = True

    def can_import_display(self, obj):

        gri = GoogleReaderImport(obj.id)

        return u'<a href="{0}">{1}</a>'.format(
                    reverse('google_reader_can_import_toggle',
                            kwargs={'user_id': obj.id}), _(u'deny')
                            if gri.can_import else _(u'allow'))

    can_import_display.short_description = _(u'Permission')
    can_import_display.allow_tags = True


admin.site.register(GriUser, GriOneFlowUserAdmin)


class TagAdmin(admin.DocumentAdmin):

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
            return u', '.join(u'<a href="/admin/models/tag/{0}" '
                              u'target="_blank">{1}</a>'.format(
                                  parent.id, parent.name)
                              for parent in obj.parents)

        return u'—'

    parents_display.short_description = _(u'Parents')
    parents_display.allow_tags = True

    def children_display(self, obj):

        if obj.children:
            return u', '.join(u'<a href="/admin/models/tag/{0}" '
                              u'target="_blank">{1}</a>'.format(
                                  child.id, child.name)
                              for child in obj.children)

        return u'—'

    children_display.short_description = _(u'Children')
    children_display.allow_tags = True


admin.site.register(Tag, TagAdmin)


class ArticleAdmin(admin.DocumentAdmin):

    list_display = ('id', 'title', 'language', 'url_absolute',
                    'date_published', 'tags_display',
                    'orphaned', 'duplicate_of_display',
                    'content_type_display',
                    'content_error_display',
                    'url_error_display', )
    #list_editable = ('language', )
    list_display_links = ('id', 'title', )
    search_fields = ('title', 'slug', )
    change_list_filter_template = "admin/filter_listing.html"
    ordering = ('-date_published', '-date_added', )
    #date_hierarchy = ('date_published', )

    raw_id_fields = ('tags', 'authors', 'publishers',
                     'source', 'duplicate_of', 'feeds', )

    def tags_display(self, obj):

        try:
            return u', '.join(u'<a href="/admin/models/tag/{0}" '
                              u'target="_blank">{1}</a>'.format(
                                  tag.id, tag.name)
                              for tag in obj.tags)
        except Exception, e:
            return unicode(e)

    tags_display.allow_tags        = True
    tags_display.short_description = _(u'Tags')
    tags_display.admin_order_field = 'tags'

    def duplicate_of_display(self, obj):

        if obj.duplicate_of:
            return (u'<a href="/admin/models/article/{0}" '
                    u'style="cursor: pointer; font-size: 300%;" '
                    u'target="_blank">∃</a>').format(obj.duplicate_of.id)

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
            'languages': HorizontalCheckbox(),
            'last_etag': TextInput(attrs={'class': 'vLargeTextField'}),
            'last_modified': TextInput(attrs={'class': 'vLargeTextField'}),
        }


class FeedAdmin(admin.DocumentAdmin):
    form = FeedAdminForm
    list_display = ('id', 'name', 'url_display',
                    'good_for_use_display', 'restricted_display',
                    'duplicate_of_display', 'errors_display',
                    'closed_display', 'fetch_interval_display',
                    'last_fetch_display',
                    'date_added_display', 'latest_article_display',
                    'recent_articles_count_display',
                    'all_articles_count_display',
                    'subscriptions_count_display', )

    # Doesn't work with mongoadmin yet
    #list_editable      = ('good_for_use', )

    list_display_links = ('id', 'name', )
    list_per_page = config.FEED_ADMIN_LIST_PER_PAGE
    search_fields = ('name', 'url', 'site_url', 'closed', )
    exclude = ('tags', )
    raw_id_fields = ('duplicate_of', )
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
            'fields': ('name', 'url',
                       ('good_for_use', 'restricted', ),
                       'languages', 'notes',
                       'date_added', ),
        }),
        ('Public information', {
            'classes': ('grp-collapse grp-open', ),
            'fields' : ('thumbnail_url',
                        'description_en', 'description_fr', ),
        }),
        ('Fetch parameters', {
            'classes': ('grp-collapse grp-closed', ),
            'fields' : ('fetch_interval', 'last_fetch',
                        'last_etag', 'last_modified', ),
        }),
        ('Errors and closing procedure', {
            'classes': ('grp-collapse grp-closed', ),
            'fields' : (('closed', 'date_closed', ),
                        'closed_reason', 'errors', ),
        }),
    )
    # def name_display(self, obj):

    #     return u'<a href="{0}" target="_blank" {2}>{1}</a>'.format(
    #         obj.site_url, obj.name, u'style="text-decoration: line-through;"'
    #         if obj.closed else '')

    # name_display.short_description = _(u'Feed name')
    # name_display.allow_tags = True
    # name_display.admin_order_field = 'name'

    def url_display(self, obj):

        return (u'<a href="{0}" target="_blank" {2}>RSS</a> '
                u'<a href="{1}" target="_blank" {1}>www</a>'.format(
                    obj.url, obj.site_url,
                    u'style="text-decoration: line-through;"'
                    if obj.closed else ''))

    url_display.short_description = _(u'URLs')
    url_display.allow_tags = True
    url_display.admin_order_field = 'url'

    def duplicate_of_display(self, obj):

        if obj.duplicate_of:
            return (u'<a href="/admin/models/feed/{0}" '
                    u'style="cursor: pointer; font-size: 300%;" '
                    u'target="_blank">∃</a>').format(obj.duplicate_of.id)

        return u''

    duplicate_of_display.allow_tags        = True
    duplicate_of_display.short_description = _(u'Duplicate of')
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

    restricted_display.short_description = _(u'Private?')
    restricted_display.admin_order_field = 'restricted'
    restricted_display.boolean = True

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

        return u'<a title="{2}" href="{0}">{1}</a>'.format(
                    reverse('feed_closed_toggle',
                            kwargs={'feed_id': obj.id}), _(u'reopen')
                            if obj.closed else _(u'close'),
                            u'Closed on {0} because of: {1}'.format(
                                obj.date_closed,
                                obj.closed_reason) if obj.closed
                                else _(u'The feed is open'))

    closed_display.short_description = _(u'Closed?')
    closed_display.allow_tags = True
    closed_display.admin_order_field = 'closed'


admin.site.register(Feed, FeedAdmin)

if settings.FULL_ADMIN:
    content_fields_names = tuple(('content_' + code)
                                 for code, lang in languages)
    content_fields_displays = tuple((field + '_display')
                                    for field in content_fields_names)

    class HelpContentAdmin(django_admin.ModelAdmin):
        list_display_links = ('name', )
        list_display       = ('name', 'ordering', 'active', ) \
            + content_fields_displays
        list_editable      = ('ordering', 'active', )
        search_fields      = ('name', ) + content_fields_names
        ordering           = ('ordering', 'name', )
        save_as            = True

    for attr, attr_name in zip(content_fields_names,
                               content_fields_displays):
        setattr(HelpContentAdmin, attr_name,
                truncate_field(HelpContent, attr))

    admin.site.register(HelpContent, HelpContentAdmin)
