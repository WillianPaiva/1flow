# -*- coding: utf-8 -*-
# Settings for 1flowapp.com

from .common import * # NOQA

# 1 == 1flowapp.com, 2 == 1flow.net
SITE_ID = 1

SERVER_EMAIL = 'chani@dev.1flow.net'
DEFAULT_FROM_EMAIL = SERVER_EMAIL

RAVEN_CONFIG = {
    'dsn': 'http://b3d8169d7f4b4c30872d1f610f7f8ca6'
            ':57e08c73890e41e4a9750c501a49d5cf@dev.1flow.net/6',
}

ALLOWED_HOSTS += [
    'localhost',
    'chani.licorn.org',
    'leto.licorn.org',
    'gurney.licorn.org'
]

# Debug-toolbar related
INSTALLED_APPS += ('debug_toolbar', )
MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', )
INTERNAL_IPS = ('127.0.0.1', )
