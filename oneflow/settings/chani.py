# -*- coding: utf-8 -*-
# Settings for 1flow.io local development
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

import socket
from sparks.django.settings import include_snippets

include_snippets(
    (
        # Don't forget to deactivate nobother when we'ge got time to
        # fix other's bugs. Just kidding…
        '000_nobother',

        # Deactivate 00_development, activate 00_production and _post_
        # to test 404/500 and switch to full production configuration.
        '00_development',
        # '00_production',

        '1flow_io_pre_common',
        'common',
        'social_auth',

        # '1flow_io_post_common',
        'constance',
        'api_keys',
        'databases',
        'cache',
        'celery',
        'mail_development',
        'common_development',
        'rosetta',
        # 'djdt',
    ),
    __file__, globals()
)

ALLOWED_HOSTS += [
    'lil.1flow.io',
    'big.1flow.io',
    'chani.licorn.org',
    'duncan.licorn.org',
    'leto.licorn.org',
    'gurney.licorn.org',
]

# We need an official public host name for all `social_auth` backends.
if socket.gethostname().lower() == 'duncan':
    SITE_DOMAIN = 'big.1flow.io'
else:
    SITE_DOMAIN = 'lil.1flow.io'

# For testing both configurations.
# ACCOUNT_OPEN_SIGNUP = False

EMAIL_HOST = '192.168.111.111'
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = '/tmp/1flow.mail'
