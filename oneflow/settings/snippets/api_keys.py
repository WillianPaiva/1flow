# -*- coding: utf-8 -*-
#
# Django API keys, all loaded from the environment,
# conforming to http://www.12factor.net/config :-D
#
u"""
Copyright 2013 Olivier Cortès <oc@1flow.io>.

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

__module_globals = globals()

for key_name in (

    # ••••••••••••••••••••••••••••••••••••••••••••• Django Social Auth API keys

    'SOCIAL_AUTH_TWITTER_KEY',
    'SOCIAL_AUTH_TWITTER_SECRET',

    # 'GOOGLE_DISPLAY_NAME',
    # 'GOOGLE_CONSUMER_KEY',
    # 'GOOGLE_CONSUMER_SECRET',
    'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY',
    'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET',

    'SOCIAL_AUTH_GITHUB_KEY',
    'SOCIAL_AUTH_GITHUB_SECRET',

    'SOCIAL_AUTH_FACEBOOK_KEY',
    'SOCIAL_AUTH_FACEBOOK_SECRET',

    # 'SOCIAL_AUTH_GOOGLE_PLUS_KEY',
    # 'SOCIAL_AUTH_GOOGLE_PLUS_SECRET',

    'SOCIAL_AUTH_LINKEDIN_KEY',
    'SOCIAL_AUTH_LINKEDIN_SECRET',

    # •••••••••••••••••••••••••••••••••••••••••••••••••••••••••• Other API keys

    'READABILITY_PARSER_SECRET',
):
    os_env = os.environ.get(key_name, None)

    if os_env is None:
        continue

    __module_globals[key_name] = os_env
