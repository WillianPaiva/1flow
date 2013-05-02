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
        'db_dev',
        'mail_dev',
        'raven_dev',
        'common_dev',
        'djdt',
    ),
    globals()
)

# Override `1flow_net` for local development
SITE_DOMAIN = 'localhost'
