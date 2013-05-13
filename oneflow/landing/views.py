# -*- coding: utf-8 -*-

import logging
import datetime

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import cache_page, never_cache


from forms import LandingPageForm
from models import LandingContent

LOGGER = logging.getLogger(__name__)


def get_all_beta_data():
    """ Return all Landing BETA related data, in a way suited to be used as::

        context.update(get_all_beta_data())

    """

    return get_translations() + get_beta_invites_left() + get_beta_time_left()


def get_beta_invites_left():

    return (('beta_invites_left',
            settings.LANDING_BETA_INVITES - User.objects.count()), )


def get_beta_time_left():

    delta = (settings.LANDING_BETA_DATE - datetime.datetime.now())

    return (('beta_time_left', delta.days * 86400 + delta.seconds), )


def get_translations():

    # We can't speed up this thing with .values_list() because
    # Transmeta's way of doing thing isn't compatible with it:
    # it would need to specify the *_lang field name, which
    # would avoid the ability to fallback to default lang if
    # the field has no translation.
    return tuple((x.name, x.content) for x in LandingContent.objects.all())


def home(request):

    context = {}

    if request.POST:
        form = LandingPageForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']

            user, created = User.objects.get_or_create(username=email,
                                                       email=email)

            if created:
                return HttpResponseRedirect(reverse('landing_thanks'))

            else:
                return HttpResponseRedirect(reverse('landing_thanks',
                                            kwargs={'already_registered':
                                            _('again')}))

    else:
        form = LandingPageForm()

    context['form'] = form

    context.update(get_all_beta_data())

    return render(request, 'landing_index.html', context)


# never cache allows to update the counter for the newly registered user.
@never_cache
def thanks(request, **kwargs):

    context = dict(already_registered=bool(
        kwargs.pop('already_registered', False)))

    context.update(get_all_beta_data())

    return render(request, 'landing_thanks.html', context)
