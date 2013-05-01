# -*- coding: utf-8 -*-
# Settings for 1flowapp.com (local development)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_development',
        '1flowapp-com',
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
