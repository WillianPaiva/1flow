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

from constance import config
from mongoengine import Q

from django.http import (
    HttpResponsePermanentRedirect,
    HttpResponseForbidden,
    HttpResponseBadRequest,
    HttpResponse
)
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _, ungettext

from endless_pagination.utils import get_page_number_from_request

from sparks.django.utils import HttpResponseTemporaryServerError

from ..forms import ReadShareForm
from ..models.nonrel import (Subscription,
                            Article, Read,
                            Folder, Tag,
                            CONTENT_TYPES_FINAL)

LOGGER = logging.getLogger(__name__)


def _rwep_generate_query_kwargs(request, **kwargs):
    """ Not a view, but an helper for read_with_endless_pagination(). """

    query_kwargs = {}
    primary_mode = None
    combinations = set()
    attributes   = Read.status_data.keys()

    # First, get the view mode we were called from.
    if kwargs.get('all', False):
        # No particular kwargs for this one, but we
        # needed to pass in the 'if' to avoid the
        # default case where we get only the unread.
        primary_mode = (u'all', False)

    else:
        for attrname in attributes:
            mykwarg = kwargs.get(attrname, None)

            if mykwarg is not None:
                primary_mode = (attrname, mykwarg)

                if mykwarg:
                    query_kwargs[attrname] = mykwarg

                else:
                    # For 2 reasons we need to negate:
                    # - old reads don't have default attribute because some
                    #   didn't exist at the time, thus the value is None in
                    #   the database.
                    # - all Reads (old and new) can have `.is_starred` == None
                    #   because False and True mean "I don't like" and "I like",
                    #   None meaning "like status not set".
                    query_kwargs[attrname + u'__ne'] = True

                if request.user.is_superuser or request.user.is_staff:
                    combinations.union(set(
                        attr2, request.GET.get(attr2, None), bool)
                        for attr2 in attributes if attr2 not in attributes
                    )

    # Then allow the user to mix with manual query
    # parameters, but check them to avoid crashes.
    for parameter, value, checker in combinations:
        if value is None:
            continue

        try:
            checked_value = checker(value)

        except:
            LOGGER.exception(u'Check %s on value "%s" of parameter %s '
                             u'failed; skipped.', checker, value, parameter)
            continue

        if checker == bool and not checked_value:
            # See before, in the for loop.
            query_kwargs[parameter + u'__ne'] = True

        else:
            query_kwargs[parameter] = checked_value

    return query_kwargs, primary_mode


def _rwep_generate_order_by(request, **kwargs):

    def check_order_by(value):
        if value in (u'date_published', u'date_added', u'id', u'title', ):
            return

        raise NotImplementedError('order_by needs love!')

    default_order_by = (u'-id', )

    if request.user.mongo.is_staff_or_superuser_and_enabled:
        order_by = request.GET.get('order_by', None)

        if order_by:
            order_by = unicode(order_by).split(',')

        else:
            order_by = default_order_by
    else:
        order_by = order_by = default_order_by

    try:
        for order in order_by:
            if order.startswith(u'-'):
                check_order_by(order[1:])
            else:
                check_order_by(order)
    except:
        LOGGER.exception(u'order_by check failed (value "%s"); '
                         u'using default.', order_by)
        order_by = default_order_by

    return order_by


def _rwep_ajax_update_counters(kwargs, query_kwargs,
                               subscription, folder,
                               user, count):

    attr_name = None

    if kwargs.get('all', False):
        attr_name = u'all_articles_count'

    elif query_kwargs.get('is_starred', False):
        attr_name = u'starred_articles_count'

    elif query_kwargs.get('is_bookmarked', False):
        attr_name = u'bookmarked_articles_count'

    elif query_kwargs.get('is_read__ne', None) is True:
        attr_name = u'unread_articles_count'

    if attr_name:
        if subscription:
            current_count = getattr(subscription, attr_name)

            if current_count != count:
                setattr(subscription, attr_name, count)

                LOGGER.info(u'Updated Subscription#%s.%s=%s for '
                            u'Read.%s (old was: %s).',
                            subscription.id, attr_name, count,
                            unicode(query_kwargs), current_count)

                # TODO: update folder with diff.

        elif folder:
            current_count = getattr(folder, attr_name)

            if current_count != count:
                setattr(folder, attr_name, count)

                LOGGER.info(u'Updated Folder#%s.%s=%s for Read.%s '
                            u'(old was: %s).', folder.id, attr_name,
                            count, unicode(query_kwargs), current_count)

                # TODO: recount()/update all subscriptions counters…

        else:
            current_count = getattr(user, attr_name)

            if current_count != count:
                setattr(user, attr_name, count)

                LOGGER.info(u'Updated User#%s.%s=%s for Read.%s '
                            u'(old was: %s).', user.id, attr_name,
                            count, query_kwargs, current_count)


def _rwep_special_update_counters(subscription, user):

    if subscription == user.web_import_subscription:
        for attr_name, count in (
            ('unread_articles_count',
             subscription.reads(is_read__ne=True).count()),
        ):
            current_count = getattr(subscription, attr_name)

            if current_count != count:
                LOGGER.info(u'Setting Import Subscription#%s.%s=%s '
                            u'(old was: %s).', subscription.id, attr_name,
                            count, current_count, )

                # subscription is really a nonrel.subscription
                setattr(subscription, attr_name, count)


def _rwep_ajax_mark_all_read(subscription, folder, user, latest_displayed_read):

    if subscription:
        subscription.mark_all_read(latest_displayed_read)

    elif folder:
        for subscription in folder.subscriptions:
            subscription.mark_all_read(latest_displayed_read)

    else:
        for subscription in user.subscriptions:
            subscription.mark_all_read(latest_displayed_read)


def _rwep_build_page_header_text(subscription, folder, user, primary_mode):

    mode, negated = primary_mode

    if mode == 'is_read' and not negated:
        mode = 'is_unread'

    attr_name = (u'all_articles_count'
                 if mode == u'all'
                 else mode[3:] + u'_articles_count')

    singular_text, plural_text = Read.status_data[mode]['list_headers']

    if subscription:
        count = getattr(subscription, attr_name)

        header_text_left = subscription.name

    elif folder:
        count     = getattr(folder, attr_name)
        sub_count = folder.subscriptions.count()

        header_text_left = folder.name + ungettext(
            u' (%(count)s subscription)',
            u' (%(count)s subscriptions)', sub_count) % {'count': sub_count}

    else:
        count     = getattr(user, attr_name)
        sub_count = user.subscriptions.count()

        header_text_left = ungettext(
            u'In your <span class="hide">%(count)s</span> subscription',
            u'In your %(count)s subscriptions', sub_count) % {
            'count': sub_count}

    header_text_right = ungettext(singular_text, plural_text, count) % {
        'count': count}

    return header_text_left, header_text_right


def read_with_endless_pagination(request, **kwargs):
    """ Central view for ALL reading lists. """

    (query_kwargs,
     primary_mode) = _rwep_generate_query_kwargs(request, **kwargs)
    order_by       = _rwep_generate_order_by(request, **kwargs)
    djuser         = request.user
    user           = djuser.mongo

    # —————————————————————————————————————————————————————— Search preparation

    search = request.GET.get('search', None)

    if request.is_ajax():
        # Ajax requests for django-endless-pagination
        # infinite scrolling. Get search query if any.
        search = request.session.get('search', None)

    else:
        # Classic access. Update the session for
        # django-endless-pagination ajax requests.
        search_cleared = search == u'' and request.session['search'] != u''

        request.session['search'] = search

        if search_cleared:
            if request.resolver_match.view_name == u'read_all':
                return redirect('source_selector')

            return redirect(request.path)

    # ———————————————————————————————————————————————————————————— Subscription

    # A “feed” (from the user point of view) is actually
    # a subscription (from the developer point of view).
    subscription = kwargs.get('feed', None)

    if subscription:
        subscription = Subscription.get_or_404(subscription)

        if subscription.user != user:
            if user.has_staff_access:

                messages.warning(request,
                                 _(u'As administrator, you are '
                                   u'accessing the feed of another user. '
                                   u'USE WITH CAUTION.'), extra_tags='sticky')

            elif user.is_staff_or_superuser_and_enabled:
                return HttpResponseForbidden(
                    u'Staff access explicitely '
                    u'denied (check config.STAFF_HAS_FULL_ACCESS)')

            else:
                return HttpResponseForbidden('Not Owner')

        query_kwargs[u'subscriptions__contains'] = subscription

    # —————————————————————————————————————————————————————————————————— Folder

    folder = kwargs.get('folder', None)

    if folder:
        folder = Folder.get_or_404(folder)

        if folder.owner != user:
            if user.has_staff_access:
                messages.warning(request,
                                 _(u'As administrator, you are '
                                   u'accessing the feed of another user. '
                                   u'USE WITH CAUTION.'), extra_tags='sticky')

            elif user.is_staff_or_superuser_and_enabled:
                return HttpResponseForbidden(
                    u'Staff access explicitely denied '
                    u'(check config.STAFF_HAS_FULL_ACCESS)')

            else:
                return HttpResponseForbidden('Not Owner')

        # LOGGER.info(u'Refining reads by folder %s', folder)

        query_kwargs[u'subscriptions__in'] = \
            Subscription.objects(folders=folder).no_cache()

    # —————————————————————————————————————————————————————————————————— Search

    if search:
        isearch = search.lower()

        # Implement these loops for multi-words search.
        for term in isearch.split():
            if term.startswith(u'+'):
                pass
            elif term.startswith(u'-'):
                pass

        if subscription:
            user_feeds = [subscription.feed]

        elif folder:
            user_feeds = [s.feed for s in Subscription.objects(folders=folder)]

        else:
            user_feeds = [s.feed for s in user.subscriptions]

        # LOGGER.info(u'Matched user feeds for search “%s”: %s',
        #            isearch, len(user_feeds))

        matched_articles = Article.objects(
            #
            # NOTE: sync these filters with core.article.is_good
            #       and core.feed.is_good
            #
            feeds__in=user_feeds,
            orphaned__ne=True,
            url_absolute=True,
            duplicate_of__exists=False,
            content_type__in=CONTENT_TYPES_FINAL).no_cache()

        # LOGGER.info(u'First-pass filtered articles for search “%s”: %s',
        #            isearch, matched_articles.count())

        matched_articles = matched_articles.filter(
            Q(title__icontains=isearch))

        #  | Q(excerpt__icontains=isearch)
        #  | Q(content__icontains=isearch))

        # LOGGER.info(u'Matched articles for search “%s”: %s',
        #            isearch, matched_articles.count())

        tags = set()

        for term in search.split():
            try:
                tag = Tag.objects.get(name=term)

            except:
                # Not a tag
                pass
            else:
                tags.add(tag)

    # ————————————————————————————————————————————————————————————— Final query

        if tags:
            reads = user.reads(**query_kwargs).filter(
                Q(tags=tag) | Q(article__in=matched_articles)).order_by(
                *order_by).no_cache()
        else:
            reads = user.reads(
                article__in=matched_articles, **query_kwargs).order_by(
                *order_by).no_cache()

    else:
        reads = user.reads(**query_kwargs).order_by(*order_by).no_cache()

    header_text_left, header_text_right = _rwep_build_page_header_text(
        subscription, folder, user, primary_mode)

    context = {
        u'reads': reads,
        u'subscription': subscription,
        u'folder': folder,
        u'current_mode': primary_mode[0],
        u'search': search,
        # 'user' is already there, via a context processor.

        u'read_page_header_text_left': header_text_left,
        u'read_page_header_text_right': header_text_right,

        # are we rendering the first "main"
        # page, or just a subset via ajax?
        u'initial': False,
    }

    # ——————————————————————————————————————————————————————————— Ajax requests

    if request.is_ajax():

        if request.GET.get('count', False):
            count = reads.count()

            #
            # Check and update cache counters
            #

            if search is None:

                try:
                    _rwep_ajax_update_counters(kwargs, query_kwargs,
                                               subscription, folder,
                                               user, count)
                except UnicodeDecodeError:
                    pass

                if subscription:
                    _rwep_special_update_counters(subscription, user)

                #
                # prepare the "inline mini-template" for ajax update.
                #

            mode, negated = primary_mode

            if mode == 'is_read' and not negated:
                mode = 'is_unread'

            singular_text, plural_text = Read.status_data[mode]['list_headers']

            if count == 0:
                rendered_text = _(u'no item')

            elif count == 1:
                rendered_text = singular_text % {'count': count}

            else:
                rendered_text = plural_text % {'count': count}

            return HttpResponse(rendered_text)

        elif request.GET.get('mark_all_read', False):

            latest_displayed_read = user.reads.get(
                article=Article.objects.get(
                    id=request.GET.get('mark_all_read')))

            _rwep_ajax_mark_all_read(subscription, folder, user,
                                     latest_displayed_read)

            return HttpResponse('DONE')

        else:
            template = u'snippets/read/read-endless-page.html'

            # Computing tenths_counter here is much efficient than doing:
            # {% captureas tenths_counter %}{{ request.GET['page']|mul:10 }}{% endcaptureas %} # NOQA
            # in the template…
            context[u'tenths_counter'] = \
                (get_page_number_from_request(request) - 1) \
                * config.READ_INFINITE_ITEMS_PER_FETCH

        # LOGGER.info(u'Ajax with %s', context.get('tenths_counter'))

    # ———————————————————————————————————————————————————— Standard GET request

    else:
        template = u'read-endless.html'
        context[u'initial'] = True

    return render(request, template, context)


def read_meta(request, read_id):
    """ Return the meta-data of a Read. """

    try:
        read = Read.get_or_404(read_id)

    except:
        return HttpResponseTemporaryServerError()

    if not request.is_ajax() and not settings.DEBUG:
        return HttpResponseBadRequest('Must be called via Ajax')

    return render(request,
                  'snippets/read/read-meta-async.html',
                  {'read': read, 'article': read.article})


def read_one(request, read_id):
    """ Generate a one-article read page (outside of a reading list).

    .. todo:: this view and its template needs refactoring / refreshing.
    """
    try:
        read = Read.get_or_404(read_id)

    except:
        return HttpResponseTemporaryServerError()

    user = request.user.mongo

    if read.user != user:
        # Most probably, a user has shared
        # his read_one() url with another user.

        cloned_read, created = user.received_items_subscription.create_read(
            article=read.article)

        cloned_read.update(add_to_set__senders=read.user)

        if created:
            message = _(u'{1} shared <em>{0}</em> with you.').format(
                read.article.title, read.user.get_full_name())
        else:
            message = _(u'Recorded <em>{0}</em> as shared by {1} '
                        u'in your inbox.').format(
                read.article.title, read.user.get_full_name())

        messages.info(request, message, extra_tags='safe')

        return HttpResponsePermanentRedirect(
            u'http://' + settings.SITE_DOMAIN
            + reverse('read_one', args=(cloned_read.id,)))

    if request.is_ajax():
        template = u'snippets/read/read-one.html'

    else:
        template = u'read-one.html'

    return render(request, template, {'read': read})


def share_one(request, article_id):
    """ Base view for sharing an article / read. """

    if not request.is_ajax():
        return HttpResponseBadRequest(u'Ajax is needed for this…')

    try:
        article = Article.get_or_404(article_id)
        read    = Read.get_or_404(article=article, user=request.user.mongo)

    except:
        LOGGER.exception(u'Could not load things to share article #%s',
                         article_id)
        return HttpResponseTemporaryServerError('BOOM')

    if request.POST:
        form = ReadShareForm(request.POST, user=request.user.mongo)

        if form.is_valid():
            sent, failed = form.save()

            if failed:
                for address, reason in failed:
                    messages.warning(request,
                                     _(u'Share article with <code>{0}</code> '
                                       u'failed: {1}').format(address, reason),
                                     extra_tags='sticky safe')

            if sent:
                messages.info(request,
                              _(u'Successfully shared <em>{0}</em> '
                                u'with {1} persons').format(
                                  read.article.title, len(sent)),
                              extra_tags='safe')

            return HttpResponse(u'DONE')

    else:
        form = ReadShareForm(user=request.user.mongo)

    return render(request, u'snippets/share/share-one.html',
                  {'read': read, 'form': form})
