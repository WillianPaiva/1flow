# -*- coding: utf-8 -*-
"""
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
    HttpResponse
)
from django.core.urlresolvers import reverse
from django.conf import settings
from django.shortcuts import render, redirect
from django.template import add_to_builtins

from sparks.django.utils import HttpResponseTemporaryServerError

from ..forms import WebPagesImportForm

from ..models.nonrel import Article, Read, CONTENT_TYPES_FINAL
from ..models.reldb import HelpContent

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

for attrkey, attrval in Read.status_data.items():
    if 'list_url' in attrval:
        # HEADS UP: sync the second argument with urls.py
        make_read_wrapper(attrkey, 'feed', attrval.get('view_name'))
        make_read_wrapper(attrkey, 'folder', attrval.get('view_name'))


# —————————————————————————————————————————————————————————————— Home / Sources


def skip_welcome_beta(request):
    """ Mark the welcome beta wizard as shown for current user.

    Then skip to the next functional view.
    """

    user = request.user.mongo

    user.preferences.wizards.welcome_beta_shown = True
    user.preferences.save()

    # NOTE: The next 3 lines of code have to
    #       be synched with the home() view.

    if user.has_content:
        return redirect('source_selector')

    return redirect('add_subscription')


def home(request):
    """ root of the application. """

    user    = request.user.mongo
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

    mongo_user     = request.user.mongo
    selector_prefs = mongo_user.preferences.selector

    return render(request, template, {
        'subscriptions':               mongo_user.subscriptions,
        'nofolder_open_subscriptions': mongo_user.nofolder_open_subscriptions,
        'closed_subscriptions':        mongo_user.nofolder_closed_subscriptions,
        'show_closed_streams':         selector_prefs.show_closed_streams,
        'titles_show_unread_count':    selector_prefs.titles_show_unread_count,
        'folders_show_unread_count':   selector_prefs.folders_show_unread_count,
    })


# ————————————————————————————————————————————————————————————————————— Various


def import_web_url(request, url):
    """ Import an URL from the web (can be anything). """

    form = WebPagesImportForm({'urls': url}, request=request)

    article = None

    if form.is_valid():
        created, failed = form.save()

        article = created[0]

        # Just in case the item was previously
        # here (from another user, or the same).
        if article.content_type in CONTENT_TYPES_FINAL:
            read = Read.get_or_404(user=request.user.mongo,
                                   article=article)

            return HttpResponsePermanentRedirect(
                u'http://' + settings.SITE_DOMAIN
                + reverse('read_one', args=(read.id,)))

    return render(request, 'import-web-url.html',
                  {'article': article, 'url': url,
                   'poll_url': reverse('article_conversion_status',
                                       args=(article.id,))})


def article_conversion_status(request, article_id):
    """ Return a 202 if article is converting, else redirect to article. """

    try:
        article = Article.get_or_404(article_id)

    except:
        return HttpResponseTemporaryServerError(
            u'Could not find article #{0}'.format(article_id))

    if article.content_type in CONTENT_TYPES_FINAL:

        read = Read.get_or_404(user=request.user.mongo, article=article)

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
        form = WebPagesImportForm(request.POST,
                                  # This is our own kwargs parameter.
                                  request=request)

        if form.is_valid():
            created, failed = form.save()

        #
        # TODO: return a JSON when request comes from browser extensions.
        #
        return render(request,
                      'snippets/selector/import-web-items-result.html',
                      {'created': created, 'failed': failed})

    else:
        form = WebPagesImportForm()

    return render(request, 'snippets/selector/import-web-pages.html',
                  {'form': form})


def help(request):
    """ Display the help section. """

    help_sections = HelpContent.objects.filter(active=True)

    return render(request, u'help.html', {'help_sections': help_sections})


# ——————————————————————————————————————————————————————————————— Views imports


from mailaccount import MailAccountListCreateView, MailAccountDeleteView  # NOQA

from folder import manage_folder, delete_folder  # NOQA

from feed import add_feed  # NOQA

from subscription import (  # NOQA
    edit_subscription, add_subscription, cancel_subscription
)

from completers import FeedsCompleterView, UserAddressBookView  # NOQA

from read import read_with_endless_pagination, read_meta, read_one, share_one  # NOQA

from article import article_content, article_image  # NOQA

from contacts import import_contacts, import_contacts_authorized  # NOQA

from preferences import (  # NOQA
    preferences,
    set_preference,
    preference_toggle,
    toggle,
)

from google_reader import (  # NOQA
    google_reader_import,
    google_reader_can_import_toggle,
    feed_closed_toggle,
    google_reader_import_stop,
    google_reader_import_status,
)
