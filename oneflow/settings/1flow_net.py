# -*- coding: utf-8 -*-
# Settings for 1flow.net (production)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_production',
        '1flow_net',
        'common',
        'db_common',
        'db_production',
        'cache_common',
        'cache_production',
        'mail_production',
        'raven_production',
        'common_production',
    ),
    globals()
)
