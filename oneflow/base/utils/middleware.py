# -*- coding: utf-8 -*-
u"""
Copyright 2012-2014 Olivier Cortès <oc@1flow.io>.

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
import sys

import logging
import traceback

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

LOGGER = logging.getLogger(__name__)


class PrintExceptionMiddleware(object):

    u""" Print exceptions on console (in DEBUG mode only).


    .. note:: this middleware disables itself — by
        raising :class:`MiddlewareNotUsed`  — if ``settings.DEBUG``
        is ``False``.

    Source: http://stackoverflow.com/a/13061129/654755 and
    Django documentation
    """

    def __init__(self):
        """ Disable this middleware if not in DEBUG mode. """

        if not settings.DEBUG:
            raise MiddlewareNotUsed

        LOGGER.debug(
            u'\n<<<<>>>> PrintExceptionMiddleware is active. <<<<>>>>\n')

    def process_response(self, request, response):
        """ Print exception if error code is 50x. """

        if response.status_code in (500, 501, 502, 503, ):
            try:
                LOGGER.debug(u'\n'.join(
                    traceback.format_exception(*sys.exc_info())))

            except:
                LOGGER.debug(traceback.format_exc())

        return response
