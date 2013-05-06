# -*- coding: utf-8 -*-
# Settings for 1flowapp.com (local development)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_development',
        '1flowapp_com',
        'common',
        'db_common',
        'db_development',
        'cache_common',
        'cache_development',
        'cache_1flowapp_com',
        'mail_development',
        'raven_development',
        'common_development',
        'rosetta',
        'djdt',
    ),
    globals()
)

# Override `1flowapp_com` for local development
SITE_DOMAIN = 'localhost'
