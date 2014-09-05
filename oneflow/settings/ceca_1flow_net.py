# -*- coding: utf-8 -*-
# Settings for 1flow.net (production)
"""
    Copyright 2013-2014 Olivier Cortès <oc@1flow.io>

    This file is part of the 1flow project.

    1flow is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.

    1flow is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public
    License along with 1flow.  If not, see http://www.gnu.org/licenses/

"""

from sparks.django.settings import include_snippets

include_snippets(
    (
        '000_nobother',
        '00_production',
        '1flow_io_pre_common',
        'common',

        # no landing page outside of 1flow.io
        #'1flow_io_post_common',
        #
        'constance',
        'api_keys',
        'databases',
        'cache',
        'celery',
        'mail_production',

        # For 1flow.io only
        #'common_production',

        #NOTE: *NEVER* 'rosetta' here. We can't get the new translations
        #   back from production to the git repo, due to to git-flow
        #   design. Which makes perfect sense in production, anyway.
    ),
    __file__, globals()
)

# Override 1flow_io_pre_common
SITE_DOMAIN = 'ceca.1flow.net'
SITE_NAME   = '1flow CECA'


# Override mail_production
EMAIL_HOST = '127.0.0.1'


# Equivalent of common_production for CECA
MANAGERS += (('John Adam', 'j.adam@ceca.asso.fr'), )
EMAIL_SUBJECT_PREFIX='[1flow CECA admin] '
ALLOWED_HOSTS += [
    'ceca.1flow.net',
    '178.32.255.67',
]
