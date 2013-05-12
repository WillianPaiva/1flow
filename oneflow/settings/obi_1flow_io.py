# -*- coding: utf-8 -*-
# Settings for obi.1flow.net (test)

import os
from sparks.django.settings import include_snippets

include_snippets(
    os.path.dirname(__file__), (
        # no debug on OBI, we need to be in "real-life-mode".
        # Sentry will help us to get to the point, anyway.
        '00_production',
        '1flow_io',
        'common',
        'db_common',
        'db_test',
        'cache_common',
        # No cache, though, in case we hit database-translations.
        'cache_development',
        'mail_production',
        # But it's a preview/test environment, still.
        'raven_test',
        'common_test',
        # Thus we get rosetta, and eventually the Django Debug toolbar.
        'rosetta',
        'djdt',
    ),
    globals()
)

# Override `1flow_io` for preview/test environment.
SITE_DOMAIN = 'obi.1flow.io'
