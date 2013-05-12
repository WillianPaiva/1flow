# -*- coding: utf-8 -*-
# Settings for 1flow.net (local development)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_development',
        # Activate this to test 404/500…
        #'00_production',
        '1flow_io',
        'common',
        'db_common',
        'db_development',
        'cache_common',
        'cache_development',
        'mail_development',
        'raven_development',
        'common_development',
        'rosetta',
        'djdt',
    ),
    globals()
)

# Override `1flow_net` for local development
SITE_DOMAIN = 'localhost'
