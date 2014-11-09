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

from django.http import (HttpResponseRedirect,
                         HttpResponseForbidden,
                         HttpResponseBadRequest,
                         HttpResponse)
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from sparks.django.utils import HttpResponseTemporaryServerError

from ..forms import (
    HomePreferencesForm,
    ReadPreferencesForm,
    SelectorPreferencesForm,
    StaffPreferencesForm,
)

LOGGER = logging.getLogger(__name__)
User = get_user_model()


def preferences(request):
    """ Return preferences view. """

    if request.POST:

        user = request.user
        preferences = user.preferences

        home_form = HomePreferencesForm(
            request.POST, instance=preferences.home)

        reading_form = ReadPreferencesForm(
            request.POST, instance=preferences.read)

        sources_form = SelectorPreferencesForm(
            request.POST, instance=preferences.selector)

        if user.is_superuser:
            staff_form = StaffPreferencesForm(
                request.POST, instance=preferences.staff)

        if home_form.is_valid() and reading_form.is_valid() \
                and sources_form.is_valid() and (
                    user.is_superuser and staff_form.is_valid()) or 1:

            # form.save() does nothing on an embedded document,
            # which needs to be saved from the container.
            preferences.home = home_form.save()
            preferences.read = reading_form.save()
            preferences.selector = sources_form.save()

            if user.is_superuser:
                preferences.staff = staff_form.save()

            if preferences.home.has_changed \
                or preferences.read.has_changed \
                or preferences.selector.has_changed or (
                    user.is_superuser and preferences.staff.has_changed):

                messages.info(request, _(u'Preferences updated.'),)

            preferences.save()

            return redirect('preferences')
    else:
        home_form = HomePreferencesForm(
            instance=request.user.preferences.home)
        reading_form = ReadPreferencesForm(
            instance=request.user.preferences.read)
        sources_form = SelectorPreferencesForm(
            instance=request.user.preferences.selector)

        if request.user.is_superuser:
            staff_form = StaffPreferencesForm(
                instance=request.user.preferences.staff)
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

    prefs = request.user.preferences

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
                             request.user)
            return HttpResponseTemporaryServerError(
                u'Could not save preference.')

    if request.is_ajax():
        return HttpResponse(u'DONE')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER',
                                reverse('home')))


def preference_toggle(request, base, sub):
    """ Handy for boolean preferences. """

    try:
        base_pref = getattr(request.user.preferences, base)
        value     = not getattr(base_pref, sub)

    except:
        return HttpResponseBadRequest(u'Bad preference name or value.')

    else:
        return set_preference(request, base, sub, value)
