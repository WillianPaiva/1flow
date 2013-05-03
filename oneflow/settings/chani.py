# -*- coding: utf-8 -*-
# Settings for 1flow.net (local development)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_development',
        '1flow_net',
        'common',
        'db_common',
        'db_development',
        'cache_common',
        'cache_development',
        'mail_development',
        'raven_development',
        'common_development',
        'djdt',
    ),
    globals()
)

# Override `1flow_net` for local development
SITE_DOMAIN = 'localhost'
