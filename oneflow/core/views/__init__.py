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

import logging

from django.http import (
    HttpResponsePermanentRedirect,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
    HttpResponse
)
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.template import add_to_builtins
from django.utils.translation import ugettext_lazy as _

from sparks.django.http import JsonResponse, human_user_agent
from sparks.django.utils import HttpResponseTemporaryServerError

from oneflow.base.utils.dateutils import now
from oneflow.base.utils.decorators import token_protected
from oneflow.base.utils.http import clean_url

from oneflow.core import forms

from ..models.common import READ_STATUS_DATA

from oneflow.base.models import Configuration

from ..models import (  # NOQA
    User,
    Article, Read,
    BaseFeed, Subscription,
    HelpContent,
    Folder,

    # Imported for `edit_field`
    Processor,
    ChainedItem,
    WebSite,
    HistoricalArticle,
    IMPORT_STATUS,
    CONTENT_TYPES_FINAL,
)

from ..gr_import import GoogleReaderImport

LOGGER = logging.getLogger(__name__)

# Avoid repetitive {% load … %} in templates.
add_to_builtins('django.templatetags.i18n')
add_to_builtins('django.templatetags.cache')
add_to_builtins('djangojs.templatetags.js')
add_to_builtins('pipeline.templatetags.compressed')
add_to_builtins('absolute.templatetags.absolute_future')
add_to_builtins('markdown_deux.templatetags.markdown_deux_tags')
add_to_builtins('widget_tweaks.templatetags.widget_tweaks')
add_to_builtins('endless_pagination.templatetags.endless')
add_to_builtins('sparks.django.templatetags.all')
add_to_builtins('oneflow.core.templatetags.coretags')
add_to_builtins('inplaceeditform.templatetags.inplace_edit')

if settings.TEMPLATE_DEBUG:
    add_to_builtins('template_debug.templatetags.debug_tags')

# ———————————————————————————————————————————————————————————————————— Wrappers
# I couldn't find any way to create an URL patterns with a (?P<…>) that
# would be merged with a default `kwargs={…}` in the same URL pattern.
#
# Thus, these small view wrappers that just do the merge.
#


def read_feed_with_endless_pagination(request, **kwargs):
    """ Wrap read_with_endless_pagination() for a feed. """

    kwargs.update({'is_read': False})  # , 'is_bookmarked': False})
    return read_with_endless_pagination(request, **kwargs)


def read_all_feed_with_endless_pagination(request, **kwargs):
    """ Wrap read_with_endless_pagination() for all feeds. """

    kwargs[u'all'] = True
    return read_with_endless_pagination(request, **kwargs)


def read_folder_with_endless_pagination(request, **kwargs):
    """ Wrap read_with_endless_pagination() for a folder. """

    kwargs.update({'is_read': False})  # , 'is_bookmarked': False})
    return read_with_endless_pagination(request, **kwargs)


def read_all_folder_with_endless_pagination(request, **kwargs):
    """ Wrap read_with_endless_pagination() for all folders. """

    kwargs[u'all'] = True
    return read_with_endless_pagination(request, **kwargs)


def make_read_wrapper(attrkey, typekey, view_name):
    """ See http://stackoverflow.com/a/3431699/654755 for why. """

    def func(request, **kwargs):
        kwargs[attrkey] = True
        return read_with_endless_pagination(request, **kwargs)

    final_func_name = 'read_{0}_{1}_with_endless_pagination'.format(view_name,
                                                                    typekey)

    globals()[final_func_name] = func


# This builds "read_later_feed_with_endless_pagination",
# 'read_later_folder_with_endless_pagination' and so on.

for attrkey, attrval in READ_STATUS_DATA.items():
    if 'list_url' in attrval:
        # HEADS UP: sync the second argument with urls.py
        make_read_wrapper(attrkey, 'feed', attrval.get('view_name'))
        make_read_wrapper(attrkey, 'folder', attrval.get('view_name'))


# —————————————————————————————————————————————————————————————— Home / Sources


def skip_welcome_beta(request):
    """ Mark the welcome beta wizard as shown for current user.

    Then skip to the next functional view.
    """

    user = request.user

    user.preferences.wizards.welcome_beta_shown = True
    user.preferences.save()

    # NOTE: The next 3 lines of code have to
    #       be synched with the home() view.

    if user.has_content:
        return redirect('source_selector')

    return redirect('add_subscription')


def home(request):
    """ root of the application. """

    user    = request.user
    wizards = user.preferences.wizards

    if wizards.welcome_beta_shown or not wizards.show_all:

        # NOTE: The next 3 lines of code have to be synched
        #       with the skip_welcome_beta() view.

        if user.has_content:
            return redirect('source_selector')

        return redirect('add_subscription')

    return render(request, 'home.html', {
        'gr_import': GoogleReaderImport(request.user.id),
    })


def source_selector(request, **kwargs):
    """ Compute and display all information sources. """

    if request.is_ajax():
        template = u'snippets/selector/selector.html'

    else:
        template = u'selector.html'

    user     = request.user
    selector_prefs = user.preferences.selector

    return render(request, template, {
        'subscriptions':               user.subscriptions,
        'nofolder_open_subscriptions': user.nofolder_open_subscriptions,
        'closed_subscriptions':        user.nofolder_closed_subscriptions,
        'show_closed_streams':         selector_prefs.show_closed_streams,
        'titles_show_unread_count':    selector_prefs.titles_show_unread_count,
        'folders_show_unread_count':   selector_prefs.folders_show_unread_count,
    })


# ————————————————————————————————————————————————————————————————————— Various


def toggle(request, klass, oid, key):
    """ Toggle any object property, given its a boolean on the DB side. """

    #
    # TODO: push notifications on error to the user.
    #

    try:
        obj = get_object_or_404(globals()[klass], id=oid)

    except:
        LOGGER.exception(u'Oops in toggle! Model “%s” not imported?', klass)
        return HttpResponseTemporaryServerError()

    if obj.user != request.user:
        return HttpResponseForbidden(u'Not owner')

    try:
        new_value = not getattr(obj, key)
        setattr(obj, key, new_value)

    except:
        msg = (u'Unable to toggle %s of %s', key, obj)
        LOGGER.exception(*msg)
        return HttpResponseTemporaryServerError(msg[0] % msg[1:])

    else:
        if key.startswith('is_'):
            date_attr = 'date_' + key[3:]

            if hasattr(obj, date_attr):
                # LOGGER.info(u'%s %s: set %s to NOW.',
                #             obj._meta.verbose_name, obj.id, date_attr)
                setattr(obj, date_attr, now() if new_value else None)

        try:
            getattr(obj, key + '_changed')()

        except AttributeError:
            pass

        except:
            LOGGER.exception(u'Unhandled exception while running '
                             u', %s.%s_changed() on %s.',
                             obj.__class__.__name__, key, obj)

        obj.save()

    if request.is_ajax():
        return HttpResponse(u'DONE.')

    else:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                    reverse('home')))


def import_web_url(request, url):
    """ Import an URL from the web (can be anything). """

    form = forms.WebPagesImportForm({'urls': url,
                                     'status': IMPORT_STATUS.MANUAL})

    article = None

    if form.is_valid():
        user_import = form.save(request.user)

        if user_import.status == IMPORT_STATUS.FINISHED:

            if 'articles' in user_import.results['created']:
                article_url = user_import.results['created']['articles'][0]

                try:
                    article = Article.objects.get(url=article_url)

                except:
                    # Just in case we hit
                    # http://dev.1flow.net/1flow/1flow/group/51970/
                    # But it should have been wrapped earlier, thus we
                    # do not do it in first intention.
                    article = Article.objects.get(url=clean_url(article_url))

                if article.content_type in CONTENT_TYPES_FINAL:
                    read = get_object_or_404(Read, user=request.user,
                                             item=article)

                    return HttpResponsePermanentRedirect(
                        reverse('read_one', args=(read.id,)))

            else:
                feed_url = user_import.results['created']['feeds'][0]

                subscription = Subscription.objects.get(
                    feed=BaseFeed.objects.get(feed_url),
                    user=request.user
                )

                return HttpResponsePermanentRedirect(
                    reverse('source_selector') + u"#" + subscription.id)

        else:
            messages.warning(
                request,
                _(u'Could not import url “<code>{0}</code>”. Check your '
                  u'latest history entry to know why.').format(url),
                extra_tags='sticky safe')

            return HttpResponsePermanentRedirect(reverse('historyentry_list'))

    return render(request, 'import-web-url.html',
                  {'article': article, 'url': url,
                   'poll_url': reverse('article_conversion_status',
                                       args=(article.id, ))})


def article_conversion_status(request, article_id):
    """ Return a 202 if article is converting, else redirect to article. """

    try:
        article = get_object_or_404(Article, id=article_id)

    except:
        return HttpResponseTemporaryServerError(
            u'Could not find article #{0}'.format(article_id))

    if article.content_type in CONTENT_TYPES_FINAL:

        read = get_object_or_404(Read, user=request.user, item=article)

        return HttpResponse(u'http://' + settings.SITE_DOMAIN +
                            reverse('read_one', args=(read.id,)))

    res = HttpResponse(u'IN PROGRESS')
    res.status = 202

    return res


def import_web_pages(request):
    """ Import multiple web pages. """

    if not request.is_ajax():
        return HttpResponseBadRequest('This request needs Ajax')

    if request.POST:
        form = forms.WebPagesImportForm(request.POST)

        if form.is_valid():
            imp_ = form.save(request.user)

        #
        # TODO: return a JSON when request comes from browser extensions.
        #
        return render(request,
                      'snippets/selector/import-web-items-result.html',
                      {'created': imp_.lines})

    else:
        form = forms.WebPagesImportForm()

    return render(request, 'snippets/selector/import-web-pages.html',
                  {'form': form})


def help(request):
    """ Display the help section. """

    help_sections = HelpContent.objects.filter(active=True)

    return render(request, u'help.html', {'help_sections': help_sections})


def admin_status(request):
    """ Create the admin status page. Long and expensive, but informational.

    References:
        Stackoverflow questions, a lot.
        Free/total space: http://stackoverflow.com/q/4260116/654755
        Disk partitions: http://stackoverflow.com/a/6397492/654755
    """

    from oneflow.base.utils import stats

    page = request.GET.get('type', None)

    if page is None:
        return render(request, 'status/index.html')

    pages = {
        'mongodb': (
            'mongodbstats', 'mongodbcollstats',
            'archivedbstats', 'archivedbcollstats',
            'host_infos_mongodb_main',  'host_infos_mongodb_archive',
            'server_status_main', 'server_status_archive',
            'cmd_line_ops_main', 'cmd_line_ops_archive',
            'mongo_statvfs',
        ),

        'celery': (
            'celery_status',
        ),

        'redis': (
            # TODO: implement this.
        ),

        'rabbitmq': (
            'rabbitmq_queues',
        ),

        'postgresql': (
            'postgresql_status',
        ),

        'system': (
            'memory',
            'partitions_status',

            # TODO: this is a mongodb function, needed in system.
            #       port it to non-mongdb status to stop depending on it.
            'host_infos',
        ),
    }

    try:

        return render(
            request,
            'status/{0}.html'.format(page),
            dict(
                (func_name, getattr(stats, func_name)())
                for func_name in pages[page]
            )
        )

    except Exception, e:
        LOGGER.exception(u'Exception while loading Ajax admin status: %s',
                         e)


def admin_command(request, **kwargs):
    """ execute a special command on the server. """

    command = kwargs.get('command', None)

    if command is None:
        return HttpResponseBadRequest('No command supplied')

    import admin_commands

    try:
        getattr(admin_commands, command)(request)

    except AttributeError:
        raise HttpResponseBadRequest(u'Unknown command “%s”' % command)

    return render(request, u'command.html', {'command': command})


@token_protected
def export_content(request, **kwargs):
    """ Export recent feeds/articles as JSON. """

    since = kwargs.get('since')
    until = kwargs.get('until', None)
    format = request.GET.get('format', 'json')
    folder_id = kwargs.get('folder_id', None)
    folder_slug = kwargs.get('folder_slug', None)

    if folder_id:
        folder = get_object_or_404(Folder, id=folder_id)

    elif folder_slug:
        folder = get_object_or_404(Folder, slug=folder_slug)

    else:
        try:
            default_user_config = Configuration.objects.get(
                name='export_feeds_default_user')

        except Configuration.DoesNotExist:
            folder = None

        else:
            folder = User.objects.get(
                username=default_user_config.value).root_folder

    if format == 'json':

        try:
            content = {
                'result': 'OK',
                'data': BaseFeed.export_content(since, until, folder=folder),
            }

        except Exception as e:
            LOGGER.exception(u'Could not export content',
                             exc_info=True, extra={'request': request})

            content = {
                'result': 'ERR',
                'sentry_id': request.sentry['id'],
                'data': unicode(e),
            }

        if human_user_agent(request):
            return JsonResponse(content, indent=2)

        return JsonResponse(content)

    else:
        return HttpResponseBadRequest(u'Unknown format “%s”' % format)


def edit_field(request, klass, oid, form_class):
    """ Edit any object field, with minimal permissions checking, via Ajax.

    For permission to succeed, request.user must be staff or the owner
    of the object.
    """

    if not request.is_ajax():
        return HttpResponseBadRequest('This request needs Ajax')

    try:
        obj_class = globals()[klass]

    except KeyError:
        LOGGER.exception(u'KeyError on “%s” in edit! Model not imported?',
                         klass)
        return HttpResponseTemporaryServerError()

    if 'history_id' in (x.name for x in obj_class._meta.fields):
        obj = get_object_or_404(obj_class, history_id=oid)

    else:
        obj = get_object_or_404(obj_class, id=oid)

    try:
        if obj.user != request.user \
                and not request.user.is_staff_or_superuser_and_enabled:
            return HttpResponseForbidden(u'Not owner nor superuser/staff')

    except AttributeError:
        if not request.user.is_staff_or_superuser_and_enabled:
            return HttpResponseForbidden(
                u'Not superuser/staff and no owner/creator field on instance')
    try:
        instance_name = obj.name

    except:
        instance_name = unicode(obj)

    form_klass = getattr(forms, form_class)

    if request.POST:
        form = form_klass(request.POST, instance=obj)

        if form.is_valid():
            obj = form.save(request.user)

        return render(request,
                      'snippets/edit_field/result.html',
                      {
                          'instance_name': instance_name,
                          'form': form,
                          'obj': obj,
                          'field_name': [f for f in form][0].name,
                          'form_class': form_class,
                          'klass': klass,
                      })

    else:
        form = form_klass(instance=obj)

    return render(request,
                  'snippets/edit_field/modal.html',
                  {
                      'instance_name': instance_name,
                      'form': form,
                      'obj': obj,
                      'field_name': [f for f in form][0].name,
                      'form_class': form_class,
                      'klass': klass,
                  })


# ——————————————————————————————————————————————————————————————— Views imports

from history import (  # NOQA
    HistoryEntryListView,
    HistoryEntryActionView,
    HistoryEntryDeleteView,
)

from mailaccount import MailAccountListCreateView, MailAccountDeleteView  # NOQA


# ———————————————————————————————————————————————————————————— Accounts & Feeds


from mailfeed import MailFeedListCreateView, MailFeedDeleteView  # NOQA

from mailfeedrule import (  # NOQA
    MailFeedRuleListCreateView,
    MailFeedRulePositionUpdateView,
    MailFeedRuleGroupUpdateView,
    MailFeedRuleDeleteView,
)

from twitteraccount import (TwitterAccountListCreateView,   # NOQA
                            TwitterAccountDeleteView)

from twitterfeed import TwitterFeedListCreateView, TwitterFeedDeleteView  # NOQA
from twitterfeedrule import (  # NOQA
   TwitterFeedRuleListCreateView,
   TwitterFeedRulePositionUpdateView,
   TwitterFeedRuleGroupUpdateView,
   TwitterFeedRuleDeleteView,
)

from processor import ProcessorListCreateView, ProcessorDeleteView  # NOQA

from processingchain import (  # NOQA
    ProcessingChainListCreateView,
    ProcessingChainDeleteView,
)

from chaineditem import (  # NOQA
    ChainedItemListCreateView,
    ChainedItemPositionUpdateView,
    ChainedItemDeleteView,
)

from staff import (  # NOQA
    StaffFeedListCreateView,
    StaffWebSiteListCreateView,
    StaffWebSiteDeleteView,
)


# —————————————————————————————————————————————————————————————— Smaller things


from folder import manage_folder, delete_folder  # NOQA

from feed import add_feed, feed_closed_toggle  # NOQA

from subscription import (  # NOQA
    edit_subscription,
    add_subscription,
    cancel_subscription
)

from completers import FeedsCompleterView, UserAddressBookView  # NOQA

from read import read_with_endless_pagination, read_meta, read_one, share_one  # NOQA

from article import article_content, article_image  # NOQA

from contacts import import_contacts, import_contacts_authorized  # NOQA

from sync import SyncNodeListCreateView, SyncNodeDeleteView  # NOQA

from preferences import (  # NOQA
    preferences,
    set_preference,
    preference_toggle,
)

from google_reader import (  # NOQA
    google_reader_import,
    google_reader_can_import_toggle,
    google_reader_import_stop,
    google_reader_import_status,
)
