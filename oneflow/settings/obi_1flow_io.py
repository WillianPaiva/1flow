# -*- coding: utf-8 -*-
# Settings for obi.1flow.net (test)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_development',
        '1flow_io',
        'common',
        'db_common',
        'db_test',
        'cache_common',
        'cache_development',
        'mail_production',
        'raven_test',
        'common_test',
        'rosetta',
        'djdt',
    ),
    globals()
)

# Override `1flow_net` for tests
SITE_DOMAIN = 'obi.1flow.io'
