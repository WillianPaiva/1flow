# -*- coding: utf-8 -*-
"""
    Copyright 2014 Olivier Cortès <oc@1flow.io>

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

from tastypie_mongoengine.resources import MongoEngineResource
#from tastypie_mongoengine.fields import ReferencedListField, ReferenceField

#from tastypie.resources import ALL
#from tastypie.fields import CharField
from tastypie.authentication import Authentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.throttle import CacheThrottle

from .models import (UrlParser, )
from ..core.models.nonrel import (Feed, )

from ..base.api import (UserResource,
                        common_authentication,
                        UserObjectsOnlyAuthorization, )

LOGGER = logging.getLogger(__name__)


class FeedResource(MongoEngineResource):

    class Meta:
        queryset = Feed.objects.all()
        allowed_methods = ('get', )
        throttle        = CacheThrottle()

        # The feed index is always allowed.
        authentication  = Authentication

        # But it is allowed read-only for now.
        authorization   = ReadOnlyAuthorization()


__all__ = ('FeedResource', )
