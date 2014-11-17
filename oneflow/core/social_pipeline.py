# -*- coding: utf-8 -*-
u"""
Copyright 2013-2014 Olivier Cortès <oc@1flow.io>.

This file is part of the 1flow project.

It provides {python,django}-social-auth pipeline helpers.

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

# from constance import config

# from django.shortcuts import redirect

from social_auth.backends.facebook import FacebookBackend
from social_auth.backends.twitter import TwitterBackend
from social_auth.backends import google

from models import (
    TwitterAccount,
    # FacebookAccount, FacebookFeed,
)


LOGGER = logging.getLogger(__name__)


def check_feeds(social_user, user, details, request, response, backend,
                is_new=False, *args, **kwargs):
    """ Create Accounts & feeds associated with social networks. """

    try:

        if isinstance(backend, FacebookBackend):
            pass

        elif isinstance(backend, google.GoogleOAuth2Backend):
            pass

        elif isinstance(backend, TwitterBackend):
            TwitterAccount.check_social_user(social_user, user, backend)

    except:
        LOGGER.exception(u'Could not check feeds for user %s from '
                         u'backend %s.', user, social_user)
