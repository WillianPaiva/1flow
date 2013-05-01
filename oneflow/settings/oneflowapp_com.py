# -*- coding: utf-8 -*-
# Settings for 1flowapp.com

from .common import * # NOQA

SITE_ID = 1

DEBUG = False
TEMPLATE_DEBUG = False

# ADMINS += (('Matthieu Chaignot', 'mc@1flow.net'), )

RAVEN_CONFIG = {
    'dsn': 'http://2854b21004cf4ea88eadb87383c0aff5'
            ':a2b8498b97b24ae0b854515d0339d0cb@dev.1flow.net/5',
}

ALLOWED_HOSTS += [
    '1flowapp.com',
    'www.1flowapp.com',
]
