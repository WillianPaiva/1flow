# -*- coding: utf-8 -*-
# Settings for 1flowapp.com

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '00_production',
        '1flowapp_com',
        'common',
        'db_common',
        'db_production',
        'mail_production',
        'raven_production',
        'common_production',
    ),
    globals()
)
