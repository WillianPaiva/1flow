# -*- coding: utf-8 -*-
import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils.translation import get_language
from forms import LandingPageForm
from models import LandingContent

LOGGER = logging.getLogger(__name__)


def get_db_translations():

    # if 'fr_FR', get only 'fr'
    lang = get_language().split('_', 1)[0]

    # Load all translated fields from database.
    # We need to explicitely define the _lang because
    # Transmeta fields don't play well with values_list().
    return LandingContent.objects.values_list('name', 'content_' + lang)


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
                                            'again'}))

    else:
        form = LandingPageForm()

    context['form'] = form

    context.update(get_db_translations())

    return render(request, 'landing_index.html', context)


def thanks(request, **kwargs):

    context = dict(already_registered=bool(
        kwargs.pop('already_registered', False)))

    context.update(get_db_translations())

    return render(request, 'landing_thanks.html', context)
