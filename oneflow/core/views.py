# -*- coding: utf-8 -*-

import logging

from django.shortcuts import render
from django.template import add_to_builtins
from django.views.decorators.cache import never_cache

LOGGER = logging.getLogger(__name__)

add_to_builtins('ember.templatetags.ember')
add_to_builtins('django.templatetags.i18n')


@never_cache
def home(request):

    return render(request, 'home.html')
