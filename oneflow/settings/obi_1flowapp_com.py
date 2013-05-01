# -*- coding: utf-8 -*-
# Settings for obi.1flowapp.com (test)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_development',
        '1flowapp-com',
        'common',
        'mail_production',
        'raven_test',
        'common_test',
        'djdt',
    ),
    globals()
)
