# -*- coding: utf-8 -*-
# Settings for 1flowapp.com

from .common import * # NOQA

SITE_ID = 2

RAVEN_CONFIG = {
    'dsn': 'http://c1bef1ae86924a17aa0a06652bb5ed5c'
            ':7639a4ef97a94d3dae06990482ba64ba@dev.1flow.net/7',
}

ALLOWED_HOSTS += [
    'obi.1flow.net',
    'test.1flow.net',
    'beta.1flow.net',
    'preview.1flow.net',
]
