
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

import os
import math
import redis
import logging

# from django.core.urlresolvers import reverse
# from django.conf import settings
from django.contrib import messages
# from async_messages import message_user

# from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import ugettext_lazy as _

# from sparks.django.http import JsonResponse, human_user_agent
# from sparks.django.utils import HttpResponseTemporaryServerError

# from oneflow.base.utils.dateutils import now
# from oneflow.base.utils.decorators import token_protected

# from oneflow.base.models import Configuration


LOGGER = logging.getLogger(__name__)


def admin_message(request, message_type, message, *args, **kwargs):
    """ send a message either via the request.user or standard LOGGER. """

    if request is None:
        getattr(LOGGER, message_type)(message, *args)

    else:
        if args:
            message = message % args

        getattr(messages, message_type)(request, message, **kwargs)


def clear_template_cache(request=None):
    """ Clear all templates cache in the corresponding DB.

    This is not a view, but will be called from a view (or not) and thus
    accepts an optional request argument. If present, a message() will be
    sent to the request.user, else the standard LOGGER thing will be used.
    """

    cache_db = os.environ.get('REDIS_CACHE_DB', None)

    if cache_db is None:
        return

    host, port, dbnum = cache_db.split(':')

    CACHE_REDIS = redis.StrictRedis(host=host, port=port, db=dbnum)

    # example: :1:template.cache.article_meta_top.e7aa62b431edc175bb57783be24413ad  # NOQA
    template_keys = CACHE_REDIS.keys('*:template.cache.*')

    num_keys = len(template_keys)

    if num_keys <= 0:
        admin_message(request, 'info', _(u'Cache is already empty.'))
        return

    for counter in range(int(math.ceil(num_keys / 100.0))):
        # print '%s → %s' % (counter * 100, ((counter + 1) * 100) - 1)

        CACHE_REDIS.delete(
            *template_keys[counter * 100:((counter + 1) * 100) - 1]
        )

    admin_message(request, 'info',
                  _(u'Cleared %s entries from cache.'),
                  num_keys)
