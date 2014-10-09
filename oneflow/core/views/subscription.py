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

from django.http import (HttpResponseRedirect,
                         HttpResponseForbidden,
                         HttpResponseBadRequest)
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils.translation import (ugettext_lazy as _,
                                      ugettext as __)

from ..forms import ManageSubscriptionForm, AddSubscriptionForm
from ..models.nonrel import Subscription

LOGGER = logging.getLogger(__name__)


def edit_subscription(request, **kwargs):
    """ Change parameters of a subscription for current user. """

    subscription_id = kwargs.pop('subscription', None)
    subscription    = Subscription.get_or_404(subscription_id)

    if request.POST:
        form = ManageSubscriptionForm(request.POST, instance=subscription)

        if form.is_valid():
            subscription = form.save()

            messages.info(request, _(u'Subscription <em>{0}</em> successfully '
                          u'modified.').format(subscription.name),
                          extra_tags='safe')

        else:
            messages.warning(request, _(u'Could not save '
                             u'subscription: {0}.').format(form.errors),
                             extra_tags='safe')

            LOGGER.error(form.errors)

        return HttpResponseRedirect(reverse('source_selector')
                                    + u"#{0}".format(subscription.id))

    else:
        if not request.is_ajax():
            return HttpResponseBadRequest('Did you forget to do an Ajax call?')

        form = ManageSubscriptionForm(instance=subscription)

    return render(request, 'snippets/selector/manage-subscription.html',
                  {'form': form, 'subscription': subscription})


def add_subscription(request, **kwargs):
    """ Subscribe current user to a feed. """

    if request.POST:
        form = AddSubscriptionForm(request.POST, owner=request.user.mongo)

        if form.is_valid():
            added = form.save()

            messages.info(request,
                          _(u'Successfully subscribed to {0} '
                            u'streams. Articles are being added progressively, '
                            u'thanks for your patience.').format(len(added)))

            return HttpResponseRedirect(reverse('source_selector')
                                        + u'#' + __(u'unclassified-streams'))

    else:
        form = AddSubscriptionForm(owner=request.user.mongo)

    context = {'form': form}

    #
    # HEADS UP: the non `in_modal` form is used during the first-connection
    #           wizard. It will help the user add feeds / subscriptions, while
    #           his/her selector is empty.
    #

    if request.is_ajax():
        context['in_modal'] = True

        template = 'snippets/selector/add-subscription.html'

    else:
        template = 'add-subscription.html'

    return render(request, template, context)


def cancel_subscription(request, **kwargs):
    """ Cancel a subscription for current user. """

    subscription_id = kwargs.pop('subscription', None)
    subscription    = Subscription.get_or_404(subscription_id)

    if not request.user.is_superuser or subscription.user != request.user.mongo:
        return HttpResponseForbidden(u'Not owner.')

    if kwargs.pop('confirm', False):
        subscription.delete()

        messages.info(request, _(u'Subscription <em>{0}</em> successfully '
                      u'cancelled.').format(subscription.name),
                      extra_tags=u'safe')

        return redirect('source_selector')

    else:
        return render(request, 'snippets/selector/cancel-subscription.html',
                      {'subscription': subscription})
