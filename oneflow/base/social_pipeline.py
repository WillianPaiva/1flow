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

from pprint import pformat
from constance import config

from django.shortcuts import redirect

from social.backends.facebook import FacebookOAuth2
from social.backends.twitter import TwitterOAuth
from social.backends import google


LOGGER = logging.getLogger(__name__)


def debug(response, **kwargs):
    """ DEBUG the social pipeline. """

    try:
        LOGGER.warning('RESPONSE: \n%s', pformat(response))
        for key, value in kwargs.items():
            LOGGER.warning('%s: \n%s', key, pformat(value))

    except:
        LOGGER.exception('BANZAï!!!!')


def get_social_avatar(**kwargs):
    """ Get the user's social avatar and store it in social-auth's DB.

    Current implementation handles facebook, Google (oauth2) and Twitter.

    """
    # get_social_avatar(): ['username', 'pipeline_index', 'uid',
    # 'storage', 'user', 'request', 'is_new', 'response', 'details',
    # 'social', 'strategy', 'new_association', 'backend']
    # LOGGER.debug(u'get_social_avatar(): %s', kwargs.keys())

    user = kwargs.get('user')

    # If user has a local avatar, don't bother checking all this.
    if user.avatar:
        return

    try:
        url = None
        backend = kwargs.get('backend')
        response = kwargs.get('response')

        if isinstance(backend, FacebookOAuth2):
            if 'id' in response:
                url = u'http://graph.facebook.com/{}/picture?type=large'.format(
                    response['id'])

        elif isinstance(backend, google.GoogleOAuth2):
            url = response.get('picture', None)

        elif isinstance(backend, TwitterOAuth):
            url = response.get('profile_image_url', None)

        if url:
            if user.avatar_url != url:
                user.avatar_url = url
                user.save()

                LOGGER.info(u'Saved new avatar for user %s from backend %s.',
                            user, backend)

        #     avatar = urlopen(url)
        #     photo = Photo(author=user, is_avatar=True)
        #     photo.picture.save(slugify(user.username+"social") + '.jpg',
        #             ContentFile(avatar.read()))
        #     photo.save()

    except:
        LOGGER.exception(u'Could not get avatar for user %s from '
                         u'backend %s.', user, backend)


def throttle_new_user_accounts(**kwargs):
    """ Deactivate newly created users if registrations are closed.

    They are also redirected to the ``social_signup_closed`` page to
    inform them about what's going on.

    .. note:: accounts still get created in the database, and we keep them.
        This is intended to be able to contact users if registrations are
        opened again later.
    """

    user = kwargs.get('user')
    is_new = kwargs.get('is_new', False)

    if is_new and not config.SOCIAL_REGISTRATION_ENABLED:
        backend = kwargs.get('backend')

        user.is_active = False
        user.save()

        LOGGER.warning(u'De-activated new user account %s from backend %s on '
                       u'the fly because social registrations are currently '
                       u'disabled.', user, backend)

        # Wrap the 'official' account view to signify the user we are closed.
        return redirect('social_signup_closed')
