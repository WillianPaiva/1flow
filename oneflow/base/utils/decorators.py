# -*- coding: utf-8 -*-
"""
Copyright 2014 Olivier Cortès <oc@1flow.io>.

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

from django.http import HttpResponseForbidden
from ..models import Configuration

LOGGER = logging.getLogger(__name__)


def token_protected(view):
    """ Protect a view with a simple token. """

    def wrapper(*args, **kwargs):

        token = kwargs.get('token', None)

        if not Configuration.check_token(token):
            return HttpResponseForbidden('Invalid token')

        return view(*args, **kwargs)

    return wrapper
