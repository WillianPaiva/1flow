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
import humanize

from django.http import (HttpResponseRedirect,
                         HttpResponseForbidden)
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from ..tasks import import_google_reader_trigger
from ..models.nonrel import Feed

from ..gr_import import GoogleReaderImport

LOGGER = logging.getLogger(__name__)
User = get_user_model()


def google_reader_import(request, user_id=None):

    if user_id is None:
        user_id      = request.user.id
        fallback_url = reverse('profile')

    else:
        if request.user.is_superuser or request.user.is_staff:
            fallback_url = reverse('admin:index')

        else:
            return HttpResponseForbidden("Access Denied")

    redirect_url = request.META.get('HTTP_REFERER', fallback_url)

    def info(text):
        messages.info(request, text)

    gri = GoogleReaderImport(user_id)

    if gri.running():
        info(_(u'An import is already running for your Google Reader data.'))
        return HttpResponseRedirect(redirect_url)

    if not gri.is_active:
        info(_(u'Google Reader import deactivated.'))
        return HttpResponseRedirect(redirect_url)

    if not gri.can_import:
        info(_(u'Your beta invite has not yet been accepted, sorry.'))
        return HttpResponseRedirect(redirect_url)

    try:
        import_google_reader_trigger(user_id)

    except ObjectDoesNotExist:
        info(_(u'You are not logged into Google Oauth or you have no token.'))
        return HttpResponseRedirect(redirect_url)

    except:
        info(_(u'Error parsing Google Oauth tokens. '
             u'Please try signout and re-signin.'))
        return HttpResponseRedirect(redirect_url)

    else:
        if request.user.is_staff or request.user.is_superuser:
            info(_(u'Google Reader import started for user ID %s.') % user_id)

        else:
            info(_(u'Google Reader import started.'))

    return HttpResponseRedirect(redirect_url)


def google_reader_can_import_toggle(request, user_id):

    gri = GoogleReaderImport(user_id)

    gri.can_import = not gri.can_import

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('admin:index')))


# This one is protected directly in urls.py
def feed_closed_toggle(request, feed_id):

    feed = Feed.objects.get(id=feed_id)

    if feed.closed:
        feed.reopen()
    else:
        feed.close(u'Closed via the admin toggle button')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('admin:index')))


def google_reader_import_stop(request, user_id):

    def info(text):
        messages.info(request, text)

    gri          = GoogleReaderImport(user_id)
    redirect_url = request.META.get('HTTP_REFERER',
                                    reverse('admin:index'))

    user = User.objects.get(id=user_id)

    if gri.running():
        gri.end(True)
        info(u'Google Reader import stopped for user %s.' % user.username)
        return HttpResponseRedirect(redirect_url)

    if not gri.is_active:
        info(u'Google Reader import deactivated!')
        return HttpResponseRedirect(redirect_url)

    if not gri.can_import:
        info(u'User %s not allowed to import.' % user.username)
        return HttpResponseRedirect(redirect_url)

    return HttpResponseRedirect(redirect_url)


def google_reader_import_status(request):
    """ An HTML snippet view. """

    #
    # NOTE: don't test gri.is_active / gri.can_import here,
    #       it is done in the template to inform the user.
    #

    gri     = GoogleReaderImport(request.user.id)
    running = gri.running()

    if running is None:
        data = {'status': 'not_started'}

    else:
        start         = gri.start()
        articles      = gri.articles()
        reads         = gri.reads()
        total_reads   = gri.total_reads()
        starred       = gri.starred()
        total_starred = gri.total_starred()

        with humanize.i18n.django_language():

            feeds = gri.feeds()

            data = {
                # -1 to avoid counting the 'starred' virtual import feed.
                'feeds': (feeds - 1) if feeds else feeds,
                'total_feeds': gri.total_feeds(),
                'reads': reads,
                'starred': starred,
                'articles': articles,
                'total_reads': total_reads,
                'total_starred': total_starred,
                'start': humanize.time.naturaltime(start),
            }

            if running:
                data.update({
                    'status': 'running',
                })

            else:
                end = gri.end()

                data.update({
                    'status': 'done',
                    'end': humanize.time.naturaltime(end),
                    'duration': humanize.time.naturaldelta(end - start),
                })

            speeds = gri.speeds()

            data['speed'] = int(speeds.get('global') * 60)

            eta = gri.eta()

            if eta:
                data['ETA'] = humanize.time.naturaltime(eta)

    data['gr_import'] = gri

    return render(request, 'snippets/google-reader-import-status.html', data)
