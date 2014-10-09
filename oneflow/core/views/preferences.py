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
                         HttpResponseBadRequest,
                         HttpResponse)
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

from sparks.django.utils import HttpResponseTemporaryServerError

from ..forms import (
    HomePreferencesForm,
    ReadPreferencesForm,
    SelectorPreferencesForm,
    StaffPreferencesForm,
)
from ...base.utils.dateutils import now

LOGGER = logging.getLogger(__name__)
User = get_user_model()


def preferences(request):
    """ Return preferences view. """

    if request.POST:
        home_form = HomePreferencesForm(
            request.POST, instance=request.user.mongo.preferences.home)

        reading_form = ReadPreferencesForm(
            request.POST, instance=request.user.mongo.preferences.read)

        sources_form = SelectorPreferencesForm(
            request.POST, instance=request.user.mongo.preferences.selector)

        if request.user.is_superuser:
            staff_form = StaffPreferencesForm(
                request.POST, instance=request.user.mongo.preferences.staff)

        if home_form.is_valid() and reading_form.is_valid() \
                and sources_form.is_valid() and (
                    request.user.is_superuser and staff_form.is_valid()) or 1:
            # form.save() does nothing on an embedded document,
            # which needs to be saved from the container.
            request.user.mongo.preferences.home = home_form.save()
            request.user.mongo.preferences.read = reading_form.save()
            request.user.mongo.preferences.selector = sources_form.save()

            if request.user.is_superuser:
                request.user.mongo.preferences.staff = staff_form.save()

            request.user.mongo.preferences.save()

            return redirect('preferences')
    else:
        home_form = HomePreferencesForm(
            instance=request.user.mongo.preferences.home)
        reading_form = ReadPreferencesForm(
            instance=request.user.mongo.preferences.read)
        sources_form = SelectorPreferencesForm(
            instance=request.user.mongo.preferences.selector)

        if request.user.is_superuser:
            staff_form = StaffPreferencesForm(
                instance=request.user.mongo.preferences.staff)
        else:
            staff_form = None

    return render(request, 'preferences.html', {
                  'home_form': home_form,
                  'reading_form': reading_form,
                  'sources_form': sources_form,
                  'staff_form': staff_form,
                  })


def set_preference(request, base, sub, value):
    """ Set a preference, via ajax or not. """

    # Do not is_staff_or_superuser_and_enabled here, else staff users
    # who have de-activated their super-powers cannot re-enable them.
    if 'staff' in base and not (request.user.is_staff
                                or request.user.is_superuser):
        return HttpResponseForbidden(u'Forbidden. BAD™.')

    prefs = request.user.mongo.preferences

    try:
        base_pref = getattr(prefs, base)
        setattr(base_pref, sub, value)

    except:
        return HttpResponseBadRequest(u'Bad preference name or value.')

    else:

        try:
            prefs.save()

        except:
            LOGGER.exception(u'Could not save preferences for user %s',
                             request.user.mongo)
            return HttpResponseTemporaryServerError(
                u'Could not save preference.')

    if request.is_ajax():
        return HttpResponse(u'DONE')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('home')))


def preference_toggle(request, base, sub):
    """ Handy for boolean preferences. """

    try:
        base_pref = getattr(request.user.mongo.preferences, base)
        value     = not getattr(base_pref, sub)

    except:
        return HttpResponseBadRequest(u'Bad preference name or value.')

    else:
        return set_preference(request, base, sub, value)


def toggle(request, klass, oid, key):
    """ Toggle any object property, given its a boolean on the DB side. """

    #
    # TODO: push notifications on error to the user.
    #

    try:
        obj = globals()[klass].get_or_404(oid)

    except:
        return HttpResponseTemporaryServerError()

    if not obj.check_owner(request.user.mongo):
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
                setattr(obj, date_attr, now())

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
