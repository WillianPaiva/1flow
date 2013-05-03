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

    lang = get_language().split('_', 1)[0]

    contents = LandingContent.objects.values_list('name', 'content_' + lang)
    context.update(contents)

    return render(request, 'landing_index.html', context)


def thanks(request, **kwargs):

    context = dict(already_registered=bool(
        kwargs.pop('already_registered', False)))

    return render(request, 'landing_thanks.html', context)
