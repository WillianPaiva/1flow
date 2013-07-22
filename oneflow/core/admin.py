# -*- coding: utf-8 -*-

import dateutil.parser

from humanize.i18n import django_language

from constance import config

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse

from .models.nonrel import Feed
from .stats import ArticlesStatistic

import mongoadmin as admin

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

    gri_reads_display.short_description = _(u'reads')

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


class FeedAdmin(admin.DocumentAdmin):

    list_display = ('id', 'name', 'errors_display', 'url_display',
                    'restricted_display',
                    'closed_display', 'fetch_interval_display',
                    'last_fetch_display',
                    'date_added_display', 'latest_article_display',
                    'recent_articles_count_display',
                    'all_articles_count_display',
                    'subscriptions_count_display', )

    list_display_links = ('id', 'name', )
    list_per_page = config.FEED_ADMIN_LIST_PER_PAGE
    search_fields = ('name', 'url', 'site_url', 'closed', )

    # Setting this makes the whole thing unsortable…
    #ordering = ('-last_fetch', )

    # The following fields don't work with mongoadmin.
    #
    #list_filter = ('closed', 'last_fetch', 'recent_articles__count', )
    #date_hierarchy = 'date_added'
    #change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

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
                obj.url, obj.site_url, u'style="text-decoration: line-through;"'
                if obj.closed else ''))

    url_display.short_description = _(u'URLs')
    url_display.allow_tags = True
    url_display.admin_order_field = 'url'

    def errors_display(self, obj):

        if obj.closed:
            return u'—'

        if obj.errors:
            last3 = [z.rsplit('@@', 1) for z in obj.errors[:3]]

            with django_language():
                return _(u'<span title="Last 3 errors:\n{0}" '
                         u'style="cursor: pointer">'
                         u'{1} error(s)</span>').format(u'\n'.join(
                             _(u'%s: %s') % (naturaltime(
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
                            obj.date_closed, obj.closed_reason) if obj.closed
                            else _(u'The feed is open'))

    closed_display.short_description = _(u'Closed?')
    closed_display.allow_tags = True
    closed_display.admin_order_field = 'closed'


admin.site.register(Feed, FeedAdmin)


class ArticlesStatisticAdmin(admin.DocumentAdmin):

    list_display = ('date_computed_display',
                    'total_count', 'markdown_display',
                    'empty_pending_display',
                    'empty_content_error_display',
                    'html_display', 'html_content_error_display',
                    'absolutes_display', 'duplicates_display',
                    'orphaned_display', 'orphaned_url_error_display',
                    'raw_fetched_count', 'raw_duplicates_count',
                    'raw_mutualized_count', )

    # list_display_links = ('id', 'name', )
    # list_per_page = config.FEED_ADMIN_LIST_PER_PAGE
    # search_fields = ('name', 'url', 'site_url', 'closed', )

    # Setting this makes the whole thing unsortable…
    ordering = ('-date_computed', )

    # The following fields don't work with mongoadmin.
    #
    #list_filter = ('closed', 'last_fetch', 'recent_articles__count', )
    #date_hierarchy = 'date_added'
    #change_list_template = "admin/change_list_filter_sidebar.html"
    #change_list_filter_template = "admin/filter_listing.html"

    def date_computed_display(self, obj):

        with django_language():
            return (u'<span title="Launched at {0}, duration: {1}" '
                    u'style="cursor: pointer">{2}</span>').format(
                        obj.date_computed.strftime('%Y-%m-%d %H:%m %z'),
                        naturaldelta(obj.duration),
                        naturaltime(obj.date_computed))

    date_computed_display.short_description = _(u'Generated')
    date_computed_display.admin_order_field = 'date_computed'
    date_computed_display.allow_tags        = True

    def markdown_display(self, obj):

        return u'%s (%.2f%%)' % (obj.markdown_count, obj.markdown_count
                                 * 100.0 / obj.total_count)

    markdown_display.short_description = _(u'Markdown')
    markdown_display.admin_order_field = 'markdown_count'

    def empty_pending_display(self, obj):

        return u'%s (%.2f%%)' % (obj.empty_pending_count,
                                 obj.empty_pending_count
                                 * 100.0 / obj.total_count)

    empty_pending_display.short_description = _(u'Pending')
    empty_pending_display.admin_order_field = 'empty_pending_count'

    def empty_content_error_display(self, obj):

        return (u'<span title="%.2f%% of empty" style="cursor:pointer">'
                u'%s (%.2f%%)</span>') % (
                    obj.empty_content_error_count
                        * 100.0 / (obj.empty_count or 1),
                    obj.empty_content_error_count,
                    obj.empty_content_error_count * 100.0 / obj.total_count)

    empty_content_error_display.short_description = _(u'Errors')
    empty_content_error_display.admin_order_field = 'empty_pending_count'
    empty_content_error_display.allow_tags        = True

    def html_display(self, obj):

        return u'%s (%.2f%%)' % (obj.html_count, obj.html_count
                                 * 100.0 / obj.total_count)

    html_display.short_description = _(u'HTML')
    html_display.admin_order_field = 'html_count'

    def html_content_error_display(self, obj):

        return (u'<span title="%.2f%% of HTML" style="cursor:pointer">'
                u'%s (%.2f%%)') % (
                    obj.html_content_error_count
                        * 100.0 / (obj.html_count or 1),
                    obj.html_content_error_count,
                    obj.html_content_error_count * 100.0 / obj.total_count)

    html_content_error_display.short_description = _(u'Errors')
    html_content_error_display.admin_order_field = 'html_content_error_count' # NOQA
    html_content_error_display.allow_tags        = True

    def absolutes_display(self, obj):

        if obj.absolutes_count:
            return u'%s (%.2f%%)' % (obj.absolutes_count,
                                     obj.absolutes_count
                                     * 100.0 / obj.total_count)
        return u'—'

    absolutes_display.short_description = _(u'Absolutes')
    absolutes_display.admin_order_field = 'absolutes_count'

    def duplicates_display(self, obj):

        if obj.duplicates_count:
            return (u'<span title="%.2f%% of absolutes" style="cursor:pointer">'
                    u'%s (%.2f%%)') % (
                        obj.duplicates_count
                            * 100.0 / (obj.absolutes_count or 1),
                        obj.duplicates_count,
                        obj.duplicates_count * 100.0 / obj.total_count)
        return u'—'

    duplicates_display.short_description = _(u'Errors')
    duplicates_display.admin_order_field = 'duplicates_count' # NOQA
    duplicates_display.allow_tags        = True

    def orphaned_display(self, obj):

        if obj.orphaned_count:
            return u'%s (%.2f%%)' % (obj.orphaned_count,
                                     obj.orphaned_count
                                     * 100.0 / obj.total_count)
        return u'—'

    orphaned_display.short_description = _(u'Orphans')
    orphaned_display.admin_order_field = 'orphaned_count'

    def orphaned_url_error_display(self, obj):

        return (u'<span title="%.2f%% of absolutes" style="cursor:pointer">'
                u'%s (%.2f%%)') % (
                    obj.orphaned_url_error_count
                        * 100.0 / (obj.absolutes_count or 1),
                    obj.orphaned_url_error_count,
                    obj.orphaned_url_error_count * 100.0 / obj.total_count)

    orphaned_url_error_display.short_description = _(u'Errors')
    orphaned_url_error_display.admin_order_field = 'orphaned_url_error_count'
    orphaned_url_error_display.allow_tags        = True


admin.site.register(ArticlesStatistic, ArticlesStatisticAdmin)
