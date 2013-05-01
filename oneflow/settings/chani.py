# -*- coding: utf-8 -*-
# Settings for 1flow.net (local development)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_development',
        '1flow-net',
        'common',
        'mail_dev',
        'raven_dev',
        'common_dev',
        'djdt',
    ),
    globals()
)
