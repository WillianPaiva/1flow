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

import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import render

from oneflow.base.utils.http import split_url

from ..models import (
    BaseFeed,
    Subscription,
    FeedIsHtmlPageException,
    create_feeds_from_url,
    subscribe_user_to_feed,
)

LOGGER = logging.getLogger(__name__)


def add_feed(request, feed_url, subscribe=True):
    """ Subscribe a user to a feed, given a feed URL.

    The :param`subscribe` parameter is set to ``False`` for staff
    members who use a different URL.
    """

    user = request.user
    feeds = []
    feed = subscription = None
    feed_exc = sub_exc = None
    created = already_subscribed = False

    # Sanitize the URL as much as possible. Try to get the REFERER if the
    # user manually typed the address in the URL bar of his browser.
    try:
        if not feed_url.startswith(u'http'):
            if request.META.get('HTTP_REFERER', None):
                proto, host_and_port, remaining = split_url(
                    request.META['HTTP_REFERER'])

                feed_url = u'{0}://{1}{2}{3}'.format(
                    proto, host_and_port,
                    u'' if feed_url.startswith(u'/') else u'/',
                    feed_url)

            else:
                LOGGER.error(u'Bad url {0} while trying to add a '
                             u'feed.'.format(feed_url))
                feed_exc = _(u'Malformed URL {0}').format(feed_url)

    except:
        LOGGER.exception(u'Very bad url {0} while trying to add a '
                         u'feed.'.format(feed_url))
        feed_exc = _(u'Very malformed url {0}').format(feed_url)

    if feed_exc is None:
        try:
            feeds = create_feeds_from_url(feed_url)

        except FeedIsHtmlPageException:
            LOGGER.exception('Potential feed at %s does not provide '
                             u'any RSS/Atom', feed_url)
            feed_exc = _(u'The website at {0} does not '
                         u'provide any RSS/Atom feed.').format(feed_url)

        except Exception as e:
            LOGGER.exception('Exception occured while creating feed from %s',
                             feed_url)
            feed_exc = _(u'Could not create any feed from '
                         u'URL {0}: {1}').format(feed_url, e)

    if feeds:
        # Taking the first is completely arbitrary, but better than nothing.
        # TODO: enhance this with a nice form to show all feeds to the user.

        for feed, created in feeds:
            if feed.user is None:
                feed.user = user
                feed.save()

        feed, created = feeds[0]

        if subscribe:

            # Then subscribe the user to this feed,
            # and don't fail if he's already subscribed.
            try:
                subscription = Subscription.objects.get(user=user, feed=feed)

            except Subscription.DoesNotExist:
                try:
                    subscription = subscribe_user_to_feed(user, feed,
                                                          background=True)

                except Exception as sub_exc:
                    LOGGER.exception(u'Failed to subscribe user %s to feed %s',
                                     user, feed)

                else:
                    # A user subscribing to a feed from the web implicitely
                    # tells us that this feed is still running. Even if for
                    # some reason we closed it in the past, it seems OK now.
                    if not feed.is_active:
                        feed.reopen()

            else:
                already_subscribed = True

    return render(request, 'add-feed.html', {
                  'feed': feed, 'created': created, 'feeds': feeds,
                  'subscription': subscription,
                  'already_subscribed': already_subscribed,
                  'subscribe': subscribe,
                  'feed_exc': feed_exc, 'sub_exc': sub_exc})


# This one is protected directly in urls.py
def feed_closed_toggle(request, feed_id):
    """ Toggle a feed closed or open from the admin. """

    feed = BaseFeed.objects.get(id=feed_id)

    if feed.is_active:
        feed.close(u'Closed via the admin toggle button')
    else:
        feed.reopen()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('admin:index')))
