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


import redis

from django.conf import settings
from django.contrib.auth import get_user_model

from oneflow.base.utils.dateutils import datetime

User = get_user_model()

# Compatibility with old code.
DjangoUser = User

REDIS = redis.StrictRedis(host=settings.REDIS_HOST,
                          port=settings.REDIS_PORT,
                          db=settings.REDIS_DB)


def long_in_the_past():
    """ Return a datetime long before 1flow existed. """

    return datetime(2007, 1, 1)

# Get all constants and strings from a module common to reldb and nonrel.
from ..common import *  # NOQA
