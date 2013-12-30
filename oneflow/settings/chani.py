# -*- coding: utf-8 -*-
# Settings for 1flow.net (local development)

MAIN_SERVER = '127.0.0.1'

import socket
from sparks.django.settings import include_snippets

include_snippets(
    (
        # Don't forget to deactivate nobother when we'ge got time to
        # fix other's bugs. Just kidding…
        '000_nobother',
        '00_development',
        # Activate this to test 404/500…
        #'00_production',
        '1flow_io',
        'common',
        'constance',
        'api_keys',
        'databases',
        'cache',
        'celery',
        'mail_development',
        'common_development',
        'rosetta',
        #'djdt',
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

EMAIL_HOST = 'gurney'
#EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
#EMAIL_FILE_PATH = '/tmp/1flow.mail'
