# -*- coding: utf-8 -*-

import logging

#from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import never_cache

from .models import UserProfile

LOGGER = logging.getLogger(__name__)


@never_cache
def unsubscribe(request, hash_code):

    profile = get_object_or_404(UserProfile, hash_code=hash_code)

    profile.email_announcements = False
    profile.renew_hash_code(commit=False)
    profile.save(update_fields=('hash_code', 'email_announcements', ))

    return render(request, 'unsubscribe.html',
                  RequestContext(request, {'email': profile.user.email}))
