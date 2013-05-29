# -*- coding: utf-8 -*-
# Settings for zero.1flow.io, a master clone used to validate migrations.

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        '000_nobother',
        '00_production',
        '1flow_io',
        'common',
        'db_common',
        'db_production',
        'cache_common',
        'cache_production',
        'mail_production',
        'raven_development',
        'common_production',
    ),
    globals()
)

# Overide real production settings, to be able to distinguish.
SITE_DOMAIN = 'zero.1flow.io'
ALLOWED_HOSTS += ['localhost', SITE_DOMAIN]
