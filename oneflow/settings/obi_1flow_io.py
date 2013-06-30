# -*- coding: utf-8 -*-
# Settings for obi.1flow.io (preview)

# If hosted on Duncan
#MAIN_SERVER = '91.121.220.149'

# If hosted on Gurney
#MAIN_SERVER = '82.236.133.193'

# Or confined to the local LXC host
MAIN_SERVER = '10.0.3.1'

from sparks.django.settings import include_snippets

include_snippets(
    (
        '000_nobother',
        # production: we don't debug on OBI,
        # we need to be in "real-life-mode",
        # as closer as possible of real production servers.
        # Sentry will help us catch errors, anyway.
        '00_production',
        '1flow_io',
        'common',
        'constance_common',
        'api_keys_preview',
        'db_common',
        'db_preview',
        'cache_common',
        'cache_development',
        'mail_production',
        # But it's a preview/test environment, still.
        'celery_preview',
        'celery_common',
        'raven_preview',
        'common_preview',
        # Thus we get rosetta, and the Django Debug toolbar.
        'rosetta',
        'djdt',
    ),
    __file__, globals()
)

# Override `1flow_io` for preview/test environment.
SITE_DOMAIN = 'obi.1flow.io'

# OBI is the master for translations and content creation / modifications,
# cf. https://trello.com/c/dJoV4xZy . Final production is synchronized
# via deployment tools.
FULL_ADMIN = True
