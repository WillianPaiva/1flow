# -*- coding: utf-8 -*-
# Settings for obi.1flow.net (test)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_development',
        '1flow-net',
        'common',
        'db_common',
        'db_test',
        'mail_production',
        'raven_test',
        'common_test',
        'djdt',
    ),
    globals()
)
