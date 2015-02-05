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

from django.conf import settings

from oneflow.core import models


def mongodb_user(request):
    """ not the most usefull context manager in the world. """

    try:
        if request.user.is_anonymous():
            return {
                u'mongodb_user': None,
                u'preferences': None,
                u'wizards': None,
            }
    except AttributeError:
        # Most probably “'WSGIRequest' object has no attribute 'user'”
        return {}

    user = request.user
    mongodb_user = user.mongo

    return {
        u'mongodb_user': mongodb_user,
        u'preferences': user.preferences,
        u'wizards': user.preferences.wizards,

        u'NONREL_ADMIN': settings.NONREL_ADMIN,
    }


def models_constants(request):
    """ Inject content types into the context.

    So we can use them by name instead of hardcoding their integer values.

    Best used with sparks's lookup() template tag.
    """

    return {
        u'ORIGINS': models.ORIGINS,
        u'CONTENT_TYPES':     models.CONTENT_TYPES,
        u'CONTENT_TYPES_FINAL':   models.CONTENT_TYPES_FINAL,

        u'IMPORT_STATUS': models.IMPORT_STATUS,

        u'CACHE_ONE_HOUR':        models.CACHE_ONE_HOUR,
        u'CACHE_ONE_DAY':         models.CACHE_ONE_DAY,
        u'CACHE_ONE_WEEK':        models.CACHE_ONE_WEEK,
        u'CACHE_ONE_MONTH':       models.CACHE_ONE_MONTH,
    }


def social_things(request):
    """ Put django social auth 1flow's specifics in the context. """

    if request.user.is_anonymous():
        return {}

    dsa = request.user.social_auth

    return {
        'has_google': dsa.filter(
            provider='google-oauth2').count() > 0,
        'social_count': dsa.all().count()
    }
